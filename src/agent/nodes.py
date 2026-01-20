from src.agent.state import AgentState
from src.agent.tools import (
    classify_intent, scan_emails, parse_pdf, extract_data,
    save_bill, add_to_rag, rag_search, query_database,
    web_search
)
from datetime import datetime, timedelta
import os
from src.config.settings import settings
from src.modules.llm_interface import LLMInterface


def intent_classifier_node(state: AgentState) -> AgentState:
    print(f"\n🎯 INTENT CLASSIFIER: Analyzing query...")
    if "intent_classification" in state.get("completed_steps", []):
        return state
    
    result = classify_intent.invoke({"user_query": state["user_query"]})
    
    if result.get("success"):
        state["intent"] = result.get("intent", "unknown")
        state["intent_confidence"] = result.get("confidence", 0.0)
        state["entities"] = result.get("entities", {})
        
        scan_type = state["entities"].get("email_scan_type", "general")
        state["completed_steps"] = state.get("completed_steps", []) + ["intent_classification"]
        print(f"   Intent: {state['intent']} | Type: {scan_type} | Confidence: {state['intent_confidence']:.2f}")
    else:
        state["errors"] = state.get("errors", []) + [f"Intent failed: {result.get('error')}"]
        state["intent"] = "unknown"
    return state


def planner_node(state: AgentState) -> AgentState:
    print(f"\n📋 PLANNER: Creating execution plan...")
    intent = state["intent"]
    
    plan = []
    
    if intent == "scan_emails":
        # Full pipeline: Gmail → Extract → Save to DB
        plan = ["email_scanner", "pdf_processor", "data_extractor", "database_saver", "response_generator"]
        print(f"   📧 Will fetch NEW emails from Gmail and save to DB")
            
    elif intent == "query_history":
        # Search existing DB only (NO Gmail!)
        plan = ["rag_retriever", "response_generator"]
        print(f"   🔍 Will search EXISTING database (no Gmail scan)")
        
    elif intent == "analyze_spending":
        plan = ["database_query", "response_generator"]
        
    elif intent == "set_reminder":
        plan = ["database_query", "reminder_creator", "response_generator"]
        
    elif intent == "find_alternatives":
        plan = ["database_query", "web_searcher", "response_generator"]
        
    elif intent == "manual_add":
        plan = ["data_extractor", "database_saver", "response_generator"]
        
    else:
        # Default: search existing data
        plan = ["rag_retriever", "response_generator"]
        print(f"   🔍 Default: Searching database")
    
    state["plan"] = plan
    state["completed_steps"] = state.get("completed_steps", []) + ["planning"]
    print(f"   Plan: {' → '.join(plan)}")
    return state


def email_scanner_node(state: AgentState) -> AgentState:
    print(f"\n📧 EMAIL SCANNER: Fetching from Gmail...")
    try:
        days = state["entities"].get("scan_days", 30)
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")

        scan_type = state["entities"].get("email_scan_type", "general")
        require_attachments = scan_type in ["bills", "invoice", "receipts", "orders"]

        # Determine inbox category based on scan type
        inbox_category_map = {
            "promotions": "promotions",
            "discounts": "promotions",
            "social": "social",
            "updates": "updates",
            "forums": "forums",
        }
        inbox_category = inbox_category_map.get(scan_type, "primary")

        print(f"   Date range: {date_from} to {date_to} ({days} days)")
        print(f"   Type: {scan_type} | Category: {inbox_category} | Attachments: {require_attachments}")

        result = scan_emails.invoke({
            "date_from": date_from,
            "date_to": date_to,
            "user_query": state["user_query"],
            "user_email": settings.EMAIL_ADDRESS,
            "max_results": settings.EMAIL_SCAN_MAX_RESULTS,
            "require_attachments": require_attachments,
            "use_filtering": True,
            "inbox_category": inbox_category,
            "days": days
        })
        
        if result.get("success"):
            state["email_scan_results"] = result
            
            if require_attachments:
                state["downloaded_files"] = [
                    att["filepath"] for email in result.get("results", []) 
                    for att in email.get("attachments", [])
                ]
            else:
                state["downloaded_files"] = []
                
            print(f"   ✅ Found {result.get('filtered_count', 0)} relevant emails")
            print(f"   ⊗ Filtered out {result.get('filtered_out', 0)} irrelevant emails")
        else:
            state["errors"] = state.get("errors", []) + [f"Scan failed: {result.get('error')}"]
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        state["errors"] = state.get("errors", []) + [f"Scanner Error: {str(e)}"]
    
    state["completed_steps"] = state.get("completed_steps", []) + ["email_scanner"]
    return state


def pdf_processor_node(state: AgentState) -> AgentState:
    print(f"\n📄 PDF PROCESSOR: Processing attachments...")
    downloaded_files = state.get("downloaded_files", [])
    parse_results = []
    
    for pdf_path in downloaded_files:
        if pdf_path.endswith('.pdf'):
            result = parse_pdf.invoke({"pdf_path": pdf_path, "use_ocr": False})
            if result.get("success"):
                parse_results.append(result)
            else:
                state["errors"].append(f"Failed parsing {os.path.basename(pdf_path)}")
    
    state["pdf_parse_results"] = parse_results
    state["completed_steps"] = state.get("completed_steps", []) + ["pdf_processor"]
    print(f"   Processed {len(parse_results)} PDFs")
    return state


def data_extractor_node(state: AgentState) -> AgentState:
    print("\n🔍 DATA EXTRACTOR: Extracting structured data...")
    scan_type = state["entities"].get("email_scan_type", "general")
    extracted_items = []

    # Extract from PDFs first (these still need individual processing)
    pdf_results = state.get("pdf_parse_results", [])
    if pdf_results:
        print(f"   Extracting from {len(pdf_results)} PDFs...")
        for pdf in pdf_results:
            if pdf.get("extracted_text"):
                result = extract_data.invoke({"text": pdf["extracted_text"], "extraction_type": scan_type})
                if result.get("success"):
                    data = result["extracted_data"]
                    data["source"] = pdf.get("file_path")
                    extracted_items.append(data)

    # Extract from email bodies - use batch processing if many emails
    if state.get("email_scan_results"):
        emails = state["email_scan_results"].get("results", [])
        if emails:
            print(f"   Extracting from {len(emails)} email bodies...")

            # For small batches, use individual extraction
            # For larger batches, batch is already done in email_scanner with filtering
            # Here we just do final extraction on already-relevant emails
            if len(emails) <= 5:
                # Small batch - individual extraction
                for email in emails:
                    result = extract_data.invoke({"text": email["body"], "extraction_type": scan_type})
                    if result.get("success"):
                        data = result["extracted_data"]
                        data["source"] = f"Email: {email['subject']}"
                        data["email_id"] = email.get("id")
                        extracted_items.append(data)
            else:
                # Larger batch - batch all email bodies into fewer LLM calls
                from src.modules.llm_interface import LLMInterface
                llm = LLMInterface(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

                # Process in batches of 5 for extraction
                batch_size = 5
                for i in range(0, len(emails), batch_size):
                    batch = emails[i:i + batch_size]
                    for email in batch:
                        result = llm.extract_data(email["body"], scan_type)
                        if result.get("success"):
                            data = result["extracted_data"]
                            data["source"] = f"Email: {email['subject']}"
                            data["email_id"] = email.get("id")
                            extracted_items.append(data)

    state["extracted_bills"] = extracted_items
    state["completed_steps"] = state.get("completed_steps", []) + ["data_extractor"]
    print(f"   ✅ Extracted {len(extracted_items)} items")
    return state


def database_saver_node(state: AgentState) -> AgentState:
    print("\n💾 DATABASE SAVER: Indexing to Vector DB...")
    saved_ids = []
    scan_type = state["entities"].get("email_scan_type", "general")

    # Debug: Show what we're working with
    extracted_bills = state.get("extracted_bills", [])
    email_scan_results = state.get("email_scan_results", {})
    print(f"   Extracted bills to save: {len(extracted_bills)}")
    print(f"   Email scan results available: {bool(email_scan_results)}")

    # Save extracted structured data
    for item in extracted_bills:
        result = save_bill.invoke({"bill_data": item})
        if result.get("success"):
            saved_ids.append(result.get("document_id", "unknown"))
        else:
            print(f"   ⚠️ Failed to save bill: {result.get('error', 'Unknown error')}")

    # CRITICAL: Save STRUCTURED email metadata to Vector DB
    if email_scan_results:
        emails = email_scan_results.get("results", [])
        print(f"   Indexing {len(emails)} emails with structured metadata...")
        
        for email in emails:
            # Create structured JSON for each email
            email_doc = {
                "type": "email",
                "category": scan_type,
                "sender": email.get("sender", ""),
                "subject": email.get("subject", ""),
                "date": email.get("date", ""),
                "body_preview": email.get("body", "")[:500],
                "summary": f"Email from {email.get('sender', '')} about {email.get('subject', '')}",
                "has_attachments": len(email.get("attachments", [])) > 0
            }
            
            # Create searchable text content
            text_content = f"""
EMAIL DOCUMENT
==============
From: {email_doc['sender']}
Subject: {email_doc['subject']}
Date: {email_doc['date']}
Category: {email_doc['category']}

Summary: {email_doc['summary']}

Body:
{email.get('body', '')[:1000]}
"""
            
            # Save to vector DB
            result = add_to_rag.invoke({
                "text": text_content,
                "metadata": email_doc
            })

            if result.get("success"):
                saved_ids.append(result.get("document_id", ""))
                print(f"   ✓ Indexed: {email.get('subject', '')[:50]}")
            else:
                print(f"   ⚠️ Failed to index email: {result.get('error', 'Unknown error')}")
    
    # Save raw PDF content
    for pdf in state.get("pdf_parse_results", []):
        if pdf.get("extracted_text"):
            add_to_rag.invoke({
                "text": pdf["extracted_text"],
                "metadata": {"type": "pdf", "path": pdf.get("file_path")}
            })

    state["saved_bill_ids"] = saved_ids
    state["completed_steps"] = state.get("completed_steps", []) + ["database_saver"]
    print(f"   ✅ Total indexed: {len(saved_ids)} documents")
    return state


def rag_indexer_node(state: AgentState) -> AgentState:
    state["completed_steps"] = state.get("completed_steps", []) + ["rag_indexer"]
    return state


def rag_retriever_node(state: AgentState) -> AgentState:
    print(f"\n🔎 RAG RETRIEVER: Searching Vector DB...")
    print(f"   Query: {state['user_query']}")
    
    try:
        res = rag_search.invoke({"query": state["user_query"], "top_k": 10})
        
        if res.get("success"):
            results = res.get("results", [])
            
            # Clean and format results to avoid serialization issues
            cleaned_results = []
            for doc in results:
                cleaned_doc = {
                    "id": str(doc.get("id", "")),
                    "text": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "relevance_score": float(doc.get("relevance_score", 0))
                }
                cleaned_results.append(cleaned_doc)
            
            state["retrieved_documents"] = cleaned_results
            print(f"   ✅ Found {len(cleaned_results)} relevant documents")
            
            for i, doc in enumerate(cleaned_results[:3], 1):
                metadata = doc.get("metadata", {})
                if metadata.get("type") == "email":
                    subject = metadata.get("subject", "No subject")[:50]
                    score = doc.get("relevance_score", 0)
                    print(f"      {i}. {subject} (Score: {score:.2f})")
        else:
            print(f"   ❌ Search failed: {res.get('error', 'Unknown error')}")
            state["retrieved_documents"] = []
    
    except Exception as e:
        print(f"   ❌ Exception in RAG retriever: {e}")
        import traceback
        traceback.print_exc()
        state["retrieved_documents"] = []
        state["errors"] = state.get("errors", []) + [f"RAG retriever error: {str(e)}"]
    
    state["completed_steps"] = state.get("completed_steps", []) + ["rag_retriever"]
    return state


def database_query_node(state: AgentState) -> AgentState:
    print(f"\n🔎 DATABASE QUERY: Searching...")
    res = query_database.invoke({"query_type": "upcoming"}) 
    if res.get("success"):
        state["database_results"] = res
    state["completed_steps"] = state.get("completed_steps", []) + ["database_query"]
    return state


def web_searcher_node(state: AgentState) -> AgentState:
    print(f"\n🌐 WEB SEARCHER: Searching...")
    res = web_search.invoke({"query": state["user_query"]})
    if res.get("success"):
        state["web_search_results"] = res.get("results", [])
    state["completed_steps"] = state.get("completed_steps", []) + ["web_searcher"]
    return state


def reminder_creator_node(state: AgentState) -> AgentState:
    """Create and store reminders for bills with due dates"""
    print("\n⏰ REMINDER CREATOR: Setting up reminders...")

    from src.modules.reminder_storage import ReminderStorage
    from src.modules.reminder_system import ReminderSystem
    import uuid

    try:
        storage = ReminderStorage(db_path="data/reminders.db")
        reminder_system = ReminderSystem(
            email_address=settings.EMAIL_ADDRESS,
            email_password=settings.EMAIL_PASSWORD
        )

        created_reminders = []
        skipped_count = 0

        # Get bills from extracted_bills or database_results
        bills_to_remind = state.get("extracted_bills", [])
        if not bills_to_remind and state.get("database_results"):
            bills_to_remind = state["database_results"].get("results", [])

        print(f"   Processing {len(bills_to_remind)} items for reminders...")

        # Get notification settings from state or use defaults
        notification_channel = state.get("entities", {}).get("notification_channel", "email")
        days_before_list = state.get("entities", {}).get("days_before", [3, 1])
        recipient = settings.EMAIL_ADDRESS  # Default to user's email

        for bill in bills_to_remind:
            # Check if bill has a due_date
            due_date = bill.get("due_date")
            if not due_date:
                skipped_count += 1
                continue

            # Create reminder schedule
            bill_id = bill.get("id") or bill.get("email_id") or str(uuid.uuid4())
            vendor = bill.get("vendor", "Unknown")

            # Use ReminderSystem to calculate reminder dates
            result = reminder_system.create_reminders(
                bill_id=bill_id,
                bill_data=bill,
                days_before=days_before_list
            )

            if result.get("success"):
                # Store each reminder in the database
                for reminder in result.get("reminders", []):
                    reminder["recipient"] = recipient
                    reminder["channel"] = notification_channel

                    reminder_id = storage.add_reminder(reminder)
                    reminder["id"] = reminder_id
                    created_reminders.append(reminder)

                    print(f"   ✓ Reminder: {vendor} - {reminder['days_before']} days before due")
            else:
                print(f"   ⚠️ Failed to create reminder for {vendor}: {result.get('error')}")

        # Store results in state
        state["reminders_created"] = created_reminders
        state["reminders_sent"] = 0  # Will be updated by scheduler

        print(f"   ✅ Created {len(created_reminders)} reminders, skipped {skipped_count} (no due date)")

        # Get reminder stats
        stats = storage.get_stats()
        print(f"   📊 Total reminders in DB: {stats.get('total', 0)} (pending: {stats.get('pending', 0)})")

    except Exception as e:
        print(f"   ❌ Error creating reminders: {e}")
        state["errors"] = state.get("errors", []) + [f"Reminder creation error: {str(e)}"]
        state["reminders_created"] = []

    state["completed_steps"] = state.get("completed_steps", []) + ["reminder_creator"]
    return state


def response_generator_node(state: AgentState) -> AgentState:
    print(f"\n💬 RESPONSE GENERATOR: Crafting response...")

    try:
        # Validate API key
        if not settings.OPENAI_API_KEY:
            error_msg = "OPENAI_API_KEY not set in environment"
            print(f"   ❌ {error_msg}")
            state["final_response"] = f"Configuration error: {error_msg}"
            state["errors"] = state.get("errors", []) + [error_msg]
            state["completed_steps"] = state.get("completed_steps", []) + ["response_generator"]
            return state

        # Format retrieved documents to be serializable
        retrieved_docs = state.get("retrieved_documents", [])
        formatted_docs = []

        for doc in retrieved_docs:
            formatted_doc = {
                "metadata": doc.get("metadata", {}),
                "text": doc.get("text", "")[:500],  # Truncate long text
                "relevance_score": float(doc.get("relevance_score", 0))
            }
            formatted_docs.append(formatted_doc)

        # Build context from retrieved data
        context = {
            "intent": state.get("intent"),
            "scan_type": state["entities"].get("email_scan_type"),
            "extracted_items": state.get("extracted_bills", [])[:5],  # Limit to 5
            "retrieved_documents": formatted_docs[:10],  # Limit to 10
            "database_results": state.get("database_results"),
            "errors": state.get("errors", [])
        }

        print(f"   Context: {len(formatted_docs)} documents")
        print(f"   Using model: {settings.OPENAI_MODEL}")

        # Use OpenAI
        llm = LLMInterface(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
        result = llm.generate_response(state["user_query"], context)

        if result.get("success"):
            response_text = result.get("response", "No response generated")
            state["final_response"] = response_text
            print(f"   ✅ Response generated")

            # Send to WhatsApp if we have useful results (not empty/error responses)
            _send_response_to_whatsapp(state, response_text)
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"   ❌ LLM Error: {error_msg}")
            state["final_response"] = f"I found the documents but couldn't generate a response. Error: {error_msg}"
            state["errors"] = state.get("errors", []) + [f"Response generation failed: {error_msg}"]

    except Exception as e:
        print(f"   ❌ Exception in response generator: {e}")
        import traceback
        traceback.print_exc()
        state["final_response"] = f"Error generating response: {str(e)}"
        state["errors"] = state.get("errors", []) + [f"Response generator exception: {str(e)}"]

    state["completed_steps"] = state.get("completed_steps", []) + ["response_generator"]
    return state


def _send_response_to_whatsapp(state: AgentState, response_text: str) -> None:
    """
    Send the AI response to WhatsApp if:
    - WhatsApp is configured
    - Response contains useful information (not 'no results found')

    Args:
        state: Current agent state
        response_text: The generated response to potentially send
    """
    from src.modules.reminder_system import ReminderSystem

    print(f"   📱 Checking WhatsApp notification...")

    # Check if WhatsApp notification is enabled
    notification_channel = settings.NOTIFICATION_CHANNEL
    print(f"   📱 Notification channel: {notification_channel}")

    if notification_channel not in ["whatsapp", "telegram"]:
        print(f"   📱 Skipping: Channel '{notification_channel}' is not whatsapp/telegram")
        return

    # Check if we have any actual results to send
    has_results = False

    # Check for extracted data
    extracted_items = state.get("extracted_bills", [])
    if extracted_items and len(extracted_items) > 0:
        has_results = True
        print(f"   📱 Found {len(extracted_items)} extracted bills")

    # Check for retrieved documents
    retrieved_docs = state.get("retrieved_documents", [])
    if retrieved_docs and len(retrieved_docs) > 0:
        has_results = True
        print(f"   📱 Found {len(retrieved_docs)} retrieved documents")

    # Check for email scan results
    email_results = state.get("email_scan_results") or {}
    email_result_list = email_results.get("results", []) if isinstance(email_results, dict) else []
    if email_result_list and len(email_result_list) > 0:
        has_results = True
        print(f"   📱 Found {len(email_result_list)} email scan results")

    # Check for database results
    db_results = state.get("database_results") or {}
    db_result_list = db_results.get("results", []) if isinstance(db_results, dict) else []
    if db_result_list and len(db_result_list) > 0:
        has_results = True
        print(f"   📱 Found {len(db_result_list)} database results")

    # If no structured results, check if we at least have a meaningful response
    if not has_results and response_text and len(response_text) > 100:
        # Send anyway if the response is substantial (more than 100 chars)
        # This handles cases where the LLM provides useful info from context
        print(f"   📱 No structured results, but response is substantial ({len(response_text)} chars)")
        has_results = True

    # Skip if no useful results found
    if not has_results:
        print("   📱 Skipping WhatsApp: No results to send")
        return

    # Check for "no results" type responses
    no_result_phrases = [
        "no results found",
        "couldn't find any",
        "could not find",
        "no matching",
        "no documents found",
        "no emails found",
        "no bills found",
        "unable to find",
        "i don't have any",
        "no information available"
    ]

    response_lower = response_text.lower()
    for phrase in no_result_phrases:
        if phrase in response_lower:
            print("   📱 Skipping WhatsApp: Response indicates no results")
            return

    # Initialize ReminderSystem with WhatsApp credentials
    try:
        print(f"   📱 Initializing notification system...")
        print(f"   📱 Twilio SID: {settings.TWILIO_ACCOUNT_SID[:10]}..." if settings.TWILIO_ACCOUNT_SID else "   📱 Twilio SID: NOT SET")
        print(f"   📱 WhatsApp From: {settings.TWILIO_WHATSAPP_FROM}")
        print(f"   📱 WhatsApp To: {settings.TWILIO_WHATSAPP_TO}")

        reminder_system = ReminderSystem(
            twilio_account_sid=settings.TWILIO_ACCOUNT_SID,
            twilio_auth_token=settings.TWILIO_AUTH_TOKEN,
            twilio_from_number=settings.TWILIO_WHATSAPP_FROM,
            twilio_to_number=settings.TWILIO_WHATSAPP_TO,
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID
        )

        # Format message with header
        scan_type = state.get("entities", {}).get("email_scan_type", "general")

        header = "🤖 *Bill Tracker Agent*\n"
        header += f"📋 Query: {state.get('user_query', 'N/A')[:100]}\n"
        header += f"🏷️ Type: {scan_type.title()}\n"
        header += "─" * 30 + "\n\n"

        full_message = header + response_text

        # Send via configured channel
        if notification_channel == "whatsapp":
            result = reminder_system.send_whatsapp_message(full_message)
            if result.get("success"):
                print("   📱 WhatsApp: Response sent successfully")
            else:
                print(f"   📱 WhatsApp: Failed to send - {result.get('error', 'Unknown error')}")

        elif notification_channel == "telegram":
            result = reminder_system.send_telegram_message(full_message)
            if result.get("success"):
                print("   📱 Telegram: Response sent successfully")
            else:
                print(f"   📱 Telegram: Failed to send - {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"   📱 Notification error: {str(e)}")


def error_handler_node(state: AgentState) -> AgentState:
    state["final_response"] = f"Errors encountered: {state['errors']}"
    return state


def route_after_intent(state: AgentState) -> str:
    return "error_handler" if state["intent"] == "unknown" else "planner"


def route_after_plan(state: AgentState) -> str:
    return state["plan"][0] if state["plan"] else "response_generator"


def should_continue(state: AgentState) -> str:
    plan = state["plan"]
    completed = state["completed_steps"]
    for step in plan:
        if step not in completed:
            return step
    return "end"