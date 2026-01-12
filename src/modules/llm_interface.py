from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Type
import json


# --- Data Models ---

class BillData(BaseModel):
    """Structured data for bills and invoices"""
    vendor: Optional[str] = Field(description="Company or vendor name")
    amount: Optional[float] = Field(description="Total amount due")
    currency: str = Field(default="USD", description="Currency code")
    due_date: Optional[str] = Field(description="Due date in YYYY-MM-DD format")
    bill_date: Optional[str] = Field(description="Invoice date in YYYY-MM-DD format")
    category: Optional[str] = Field(description="Category (utility, subscription, etc.)")
    invoice_number: Optional[str] = Field(description="Invoice or account number")
    line_items: List[str] = Field(default=[], description="Summary of main line items")


class PromotionData(BaseModel):
    """Structured data for marketing emails and offers"""
    vendor: str = Field(description="Company offering the promotion")
    promo_code: Optional[str] = Field(description="Discount code if available")
    discount_details: str = Field(description="Description of the discount (e.g., '50% off')")
    expiration_date: Optional[str] = Field(description="Expiration date YYYY-MM-DD")
    product_category: Optional[str] = Field(description="What products are on sale")


class OrderData(BaseModel):
    """Structured data for order confirmations"""
    vendor: str = Field(description="Store name")
    order_number: Optional[str] = Field(description="Order ID")
    order_date: Optional[str] = Field(description="Date of purchase YYYY-MM-DD")
    total_amount: Optional[float] = Field(description="Total cost")
    items: List[str] = Field(description="List of items purchased")
    delivery_status: Optional[str] = Field(description="Estimated delivery or status")


class GeneralData(BaseModel):
    """Fallback for unknown types"""
    summary: str = Field(description="Brief summary of the email content")
    key_dates: List[str] = Field(default=[], description="Any important dates mentioned")
    entities: List[str] = Field(default=[], description="Names of companies or people")


class IntentClassification(BaseModel):
    """User intent classification"""
    intent: str = Field(description="Primary intent")
    scan_type: Optional[str] = Field(description="Email type if scanning")
    confidence: float = Field(description="Confidence score 0-1")
    entities: Dict = Field(default={}, description="Extracted parameters")


class RelevanceEvaluation(BaseModel):
    """Document relevance evaluation"""
    is_relevant: bool = Field(description="Whether document is relevant")
    relevance_score: float = Field(description="Score 0-1")
    reasoning: str = Field(description="Explanation")


class BatchRelevanceItem(BaseModel):
    """Single item in batch relevance evaluation"""
    email_index: int = Field(description="Index of the email (1-based)")
    is_relevant: bool = Field(description="Whether email is relevant")
    score: float = Field(description="Relevance score 0-1")
    reason: str = Field(description="Brief reason")


class BatchRelevanceResult(BaseModel):
    """Batch relevance evaluation result"""
    evaluations: List[BatchRelevanceItem] = Field(description="List of evaluations for each email")


class CombinedEvalExtractResult(BaseModel):
    """Combined relevance evaluation and data extraction"""
    is_relevant: bool = Field(description="Whether document is relevant to the query")
    relevance_score: float = Field(description="Relevance score 0-1")
    reasoning: str = Field(description="Why relevant or not")
    extracted_data: Optional[Dict] = Field(default=None, description="Extracted structured data if relevant, null otherwise")


class LLMInterface:
    
    def __init__(self, api_key: str, model: str = "", temperature: float = 0.1):
        self.model_name = model
        self.temperature = temperature
        self.llm = ChatOpenAI(model=model, api_key=api_key, temperature=temperature)
        
        self.extraction_registry = {
            "bills": BillData, "invoice": BillData,
            "promotions": PromotionData, "discounts": PromotionData,
            "orders": OrderData, "receipts": OrderData, "shipping": OrderData,
            "general": GeneralData
        }

    def _get_model_for_type(self, extraction_type: str) -> Type[BaseModel]:
        return self.extraction_registry.get(extraction_type.lower(), GeneralData)
        
    def extract_data(self, text: str, extraction_type: str = "bills") -> Dict:
        pydantic_model = self._get_model_for_type(extraction_type)
        parser = PydanticOutputParser(pydantic_object=pydantic_model)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"Extract {extraction_type} data."),
            ("human", "{format_instructions}\n\nText:\n{text}\n\nProvide data:")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"text": text, "format_instructions": parser.get_format_instructions()})
            return {"success": True, "extracted_data": result.dict(), "type": extraction_type}
        except Exception as e:
            return {"success": False, "error": str(e), "extracted_data": {}}
    
    def classify_intent(self, user_query: str) -> Dict:
        """CRITICAL: Distinguish scan_emails (fetch from Gmail) vs query_history (search DB)"""
        parser = PydanticOutputParser(pydantic_object=IntentClassification)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier. CRITICAL DISTINCTION:

**scan_emails** = Fetch NEW emails from Gmail
  Triggers: "scan", "check", "get", "fetch", "find", "search my inbox"
  Examples: "Scan for university emails", "Get emails from last week"

**query_history** = Search ALREADY SCANNED emails in database
  Triggers: "what", "show", "tell me", "do I have", "did you find", "got", "is there"
  Examples: "What emails did you find?", "Do I have any Germany emails?"

For scan_emails, extract scan_type: bills, promotions, universities, orders, general
For query_history, extract search keywords to entities"""),
            ("human", "{format_instructions}\n\nQuery: {query}\n\nClassify:")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"query": user_query, "format_instructions": parser.get_format_instructions()})
            entities = result.entities
            if result.scan_type:
                entities['email_scan_type'] = result.scan_type
            return {"success": True, "intent": result.intent, "confidence": result.confidence, "entities": entities}
        except Exception as e:
            return {"success": False, "error": str(e), "intent": "unknown", "confidence": 0.0, "entities": {}}
    
    def generate_response(self, user_query: str, context: Dict, system_prompt: Optional[str] = None) -> Dict:
        if not system_prompt:
            system_prompt = "You are a helpful email assistant. Summarize emails clearly with sender, subject, date."
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Context:\n{context}\n\nQuestion: {query}\n\nResponse:")
        ])
        
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({"context": json.dumps(context, indent=2, default=str), "query": user_query})
            return {"success": True, "response": result.content}
        except Exception as e:
            return {"success": False, "error": str(e), "response": "Error generating response."}
            
    def evaluate_relevance(self, query: str, document: str) -> Dict:
        parser = PydanticOutputParser(pydantic_object=RelevanceEvaluation)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Evaluate if email (sender, subject, body) is relevant to query. Be intelligent."),
            ("human", "{format_instructions}\n\nQuery: {query}\n\nDocument: {document}\n\nEvaluate:")
        ])

        chain = prompt | self.llm | parser

        try:
            result = chain.invoke({"query": query, "document": document, "format_instructions": parser.get_format_instructions()})
            return {"success": True, "is_relevant": result.is_relevant, "relevance_score": result.relevance_score, "reasoning": result.reasoning}
        except Exception as e:
            return {"success": False, "error": str(e), "is_relevant": False, "relevance_score": 0.0, "reasoning": "Error"}

    def batch_evaluate_relevance(self, query: str, emails: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        Evaluate multiple emails in a single LLM call to reduce token usage.
        Returns list of relevance evaluations matching the input email order.
        """
        if not emails:
            return []

        all_results = []

        # Process in batches
        for batch_start in range(0, len(emails), batch_size):
            batch = emails[batch_start:batch_start + batch_size]

            # Format all emails in batch
            batch_text = ""
            for i, email in enumerate(batch, 1):
                sender = email.get('sender', 'Unknown')[:50]
                subject = email.get('subject', 'No subject')[:100]
                body_preview = email.get('body', '')[:400]
                batch_text += f"""
---EMAIL {i}---
From: {sender}
Subject: {subject}
Preview: {body_preview}
"""

            parser = PydanticOutputParser(pydantic_object=BatchRelevanceResult)

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an email relevance evaluator. Evaluate each email's relevance to the user's query.
Be intelligent about matching - consider semantic meaning, not just keywords.
Score 0.0-0.3 = not relevant, 0.4-0.6 = possibly relevant, 0.7-1.0 = highly relevant."""),
                ("human", """{format_instructions}

User Query: {query}

Emails to evaluate:
{batch_text}

Evaluate ALL {count} emails and return evaluations for each.""")
            ])

            chain = prompt | self.llm | parser

            try:
                result = chain.invoke({
                    "query": query,
                    "batch_text": batch_text,
                    "count": len(batch),
                    "format_instructions": parser.get_format_instructions()
                })

                # Map results back to emails
                eval_map = {e.email_index: e for e in result.evaluations}
                for i in range(1, len(batch) + 1):
                    if i in eval_map:
                        e = eval_map[i]
                        all_results.append({
                            "is_relevant": e.is_relevant,
                            "score": e.score,
                            "reason": e.reason
                        })
                    else:
                        # Default to include if missing
                        all_results.append({
                            "is_relevant": True,
                            "score": 0.5,
                            "reason": "No evaluation returned, included by default"
                        })

            except Exception as e:
                print(f"   ⚠️ Batch evaluation failed: {e}")
                # On error, default to include all emails in batch
                for _ in batch:
                    all_results.append({
                        "is_relevant": True,
                        "score": 0.5,
                        "reason": f"Batch evaluation failed: {str(e)[:50]}"
                    })

        return all_results

    def evaluate_and_extract(self, query: str, email: Dict, extraction_type: str = "general") -> Dict:
        """
        Single LLM call to both evaluate relevance AND extract data.
        Reduces 2 API calls to 1 per email.
        """
        sender = email.get('sender', 'Unknown')
        subject = email.get('subject', 'No subject')
        body = email.get('body', '')[:1500]

        # Get the schema for the extraction type
        pydantic_model = self._get_model_for_type(extraction_type)
        schema_fields = list(pydantic_model.model_fields.keys())

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an email analyzer. For the given email and query:
1. Determine if the email is relevant to the query (score 0-1)
2. If relevant (score >= 0.5), extract structured {extraction_type} data

Extraction fields for {extraction_type}: {', '.join(schema_fields)}

Respond with JSON containing:
- is_relevant: boolean
- relevance_score: float 0-1
- reasoning: string explaining relevance
- extracted_data: object with extracted fields if relevant, null if not relevant"""),
            ("human", """Query: {query}

Email:
From: {sender}
Subject: {subject}
Body: {body}

Analyze and respond with JSON:""")
        ])

        chain = prompt | self.llm

        try:
            result = chain.invoke({
                "query": query,
                "sender": sender,
                "subject": subject,
                "body": body
            })

            # Parse the response
            content = result.content
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "success": True,
                    "is_relevant": parsed.get("is_relevant", False),
                    "relevance_score": parsed.get("relevance_score", 0.0),
                    "reasoning": parsed.get("reasoning", ""),
                    "extracted_data": parsed.get("extracted_data")
                }
            else:
                return {
                    "success": False,
                    "is_relevant": True,
                    "relevance_score": 0.5,
                    "reasoning": "Could not parse response",
                    "extracted_data": None
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_relevant": True,
                "relevance_score": 0.5,
                "reasoning": f"Error: {str(e)}",
                "extracted_data": None
            }

    def batch_evaluate_and_extract(self, query: str, emails: List[Dict], extraction_type: str = "general") -> List[Dict]:
        """
        Process multiple emails with combined evaluation and extraction.
        Uses batch evaluation first, then only extracts data from relevant emails.
        """
        if not emails:
            return []

        # Step 1: Batch evaluate relevance (single API call for multiple emails)
        relevance_results = self.batch_evaluate_relevance(query, emails)

        # Step 2: For relevant emails, extract data (can be batched or individual)
        final_results = []
        for i, (email, relevance) in enumerate(zip(emails, relevance_results)):
            if relevance.get("is_relevant", False) and relevance.get("score", 0) >= 0.5:
                # Extract data for relevant emails
                extract_result = self.extract_data(email.get("body", ""), extraction_type)
                final_results.append({
                    "email_index": i,
                    "is_relevant": True,
                    "relevance_score": relevance.get("score", 0.5),
                    "reasoning": relevance.get("reason", ""),
                    "extracted_data": extract_result.get("extracted_data") if extract_result.get("success") else None,
                    "email": email
                })
            else:
                final_results.append({
                    "email_index": i,
                    "is_relevant": False,
                    "relevance_score": relevance.get("score", 0),
                    "reasoning": relevance.get("reason", "Not relevant"),
                    "extracted_data": None,
                    "email": email
                })

        return final_results