from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import base64
from typing import Dict, Optional
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from src.modules.llm_interface import LLMInterface
from src.config.settings import settings

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Keywords for quick pre-filtering (before LLM)
SCAN_TYPE_KEYWORDS = {
    "bills": ["invoice", "bill", "payment", "due", "amount", "statement", "balance", "receipt"],
    "promotions": ["sale", "discount", "offer", "deal", "off", "promo", "coupon", "save", "free"],
    "universities": ["university", "admission", "application", "offer", "scholarship", "college", "student", "enrollment", "accepted"],
    "orders": ["order", "confirmation", "purchase", "shipped", "delivery", "tracking", "receipt"],
    "shipping": ["shipped", "delivery", "tracking", "package", "courier", "arrived", "transit"],
    "banking": ["bank", "statement", "transaction", "balance", "account", "transfer", "credit", "debit"],
    "insurance": ["insurance", "policy", "claim", "premium", "coverage", "renewal"],
    "travel": ["booking", "flight", "hotel", "reservation", "itinerary", "travel", "trip"],
    "tax": ["tax", "1099", "w-2", "w2", "return", "irs", "refund"],
}


def quick_keyword_filter(email: dict, user_query: str, scan_type: str = "general") -> bool:
    """
    Fast keyword-based pre-filter before LLM evaluation.
    Returns True if email should be sent to LLM for deeper evaluation.
    Returns False to skip LLM entirely (obvious non-match).
    """
    # For general scan type, be permissive - let LLM decide
    if scan_type == "general" or scan_type not in SCAN_TYPE_KEYWORDS:
        return True

    subject = email.get('subject', '').lower()
    sender = email.get('sender', '').lower()
    body_preview = email.get('body', '')[:500].lower()

    combined_text = f"{subject} {sender} {body_preview}"

    # Extract keywords from user query
    query_words = set(user_query.lower().split())
    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'for', 'from', 'my', 'me', 'i', 'to', 'and', 'or', 'in', 'on', 'at', 'of', 'scan', 'check', 'get', 'find', 'search', 'emails', 'email', 'inbox'}
    query_keywords = query_words - stop_words

    # Check if any query keyword appears in email
    for kw in query_keywords:
        if len(kw) > 2 and kw in combined_text:
            return True

    # Check scan type specific keywords
    type_keywords = SCAN_TYPE_KEYWORDS.get(scan_type, [])
    for kw in type_keywords:
        if kw in combined_text:
            return True

    # If no keywords match, still include emails with attachments for bill types
    if scan_type in ["bills", "invoice", "receipts", "orders"]:
        if email.get('attachments') or 'attachment' in combined_text or 'pdf' in combined_text:
            return True

    # Default: skip if no keyword matches (will be filtered out before LLM)
    return False


class EmailScanner:
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.download_dir = "data/raw/attachments"
        os.makedirs(self.download_dir, exist_ok=True)
        self.filtered_emails_log = []
    
    def authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def _is_relevant_via_llm(self, user_query: str, sender: str, subject: str, body: str) -> Dict[str, any]:        
        try:
            # LLM reads FULL email content
            email_content = f"""From: {sender}
Subject: {subject}

Body:
{body[:2500]}"""  # Increased limit for more context
            
            llm = LLMInterface(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
            result = llm.evaluate_relevance(query=user_query, document=email_content)
            
            return {
                "is_relevant": result.get("is_relevant", False),
                "score": result.get("relevance_score", 0.0),
                "reason": result.get("reasoning", "")
            }
        except Exception as e:
            print(f"   ⚠️ LLM relevance check failed: {e}")
            return {"is_relevant": True, "score": 1.0, "reason": "LLM check failed, included by default"}
    
    def _sanitize_filename(self, text: str) -> str:
        safe = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return re.sub(r'\s+', '_', safe.strip())

    def _download_attachment(self, message_id: str, attachment_id: str, filename: str) -> str:
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            filepath = os.path.join(self.download_dir, filename)
            
            counter = 1
            base_name = filename
            while os.path.exists(filepath):
                name, ext = os.path.splitext(base_name)
                filepath = os.path.join(self.download_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            return filepath
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            return None
    
    def _get_message_body(self, payload):
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    body = self._get_message_body(part)
                    if body: break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        return body
    
    def scan(self,
             date_from: str,
             date_to: str,
             user_query: Optional[str] = None,
             user_email: Optional[str] = None,
             max_results: int = 50,
             require_attachments: bool = True,
             use_filtering: bool = True,
             inbox_category: str = "primary",
             days: int = None) -> Dict:

        if not self.service:
            self.authenticate()

        self.filtered_emails_log = []

        # Build query with explicit inbox targeting
        # Use newer_than for short timeframes (more reliable than date range)
        if days and days <= 30:
            if inbox_category == "all":
                query = f'in:inbox newer_than:{days}d'
            elif inbox_category in ["primary", "promotions", "social", "updates", "forums"]:
                query = f'in:inbox category:{inbox_category} newer_than:{days}d'
            else:
                query = f'in:inbox category:primary newer_than:{days}d'
        else:
            # Use date range for longer periods
            if inbox_category == "all":
                query = f'in:inbox after:{date_from} before:{date_to}'
            elif inbox_category in ["primary", "promotions", "social", "updates", "forums"]:
                query = f'in:inbox category:{inbox_category} after:{date_from} before:{date_to}'
            else:
                query = f'in:inbox category:primary after:{date_from} before:{date_to}'

        if require_attachments:
            query += ' has:attachment'

        # Exclude user's own sent emails
        if user_email:
            query += f' -from:{user_email}'

        print(f"Searching Gmail: {query}")

        # Get scan_type for keyword filtering
        scan_type = "general"
        if user_query:
            for stype in SCAN_TYPE_KEYWORDS.keys():
                if stype in user_query.lower():
                    scan_type = stype
                    break

        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return {"success": True, "emails_found": 0, "filtered_count": 0, "filtered_out": 0, "results": []}

            # PHASE 1: Fetch all emails first (no LLM calls yet)
            print(f"   Fetching {len(messages)} emails...")
            all_emails = []
            message_map = {}  # Map email data to original message for attachment download

            for msg in messages:
                try:
                    message = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    headers = message['payload']['headers']

                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No_Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    body = self._get_message_body(message['payload'])

                    email_data = {
                        "id": msg['id'],
                        "subject": subject,
                        "sender": sender,
                        "date": date_str,
                        "body": body[:2000],
                        "payload": message['payload']  # Keep for attachment download
                    }
                    all_emails.append(email_data)
                    message_map[msg['id']] = message

                except Exception as msg_err:
                    print(f"Error fetching message {msg.get('id')}: {msg_err}")
                    continue

            print(f"   Fetched {len(all_emails)} emails")

            # PHASE 2: Quick keyword pre-filter (no LLM)
            if use_filtering and user_query:
                candidates = []
                quick_filtered_out = 0

                for email in all_emails:
                    if quick_keyword_filter(email, user_query, scan_type):
                        candidates.append(email)
                    else:
                        quick_filtered_out += 1
                        self.filtered_emails_log.append({
                            "subject": email["subject"],
                            "sender": email["sender"],
                            "reason": "Quick filter: no keyword match",
                            "score": 0.0
                        })

                print(f"   Quick filter: {len(candidates)} candidates, {quick_filtered_out} skipped")
            else:
                candidates = all_emails

            # PHASE 3: Batch LLM relevance check (one API call per batch of 10)
            email_results = []
            files_downloaded = 0
            filtered_out_count = 0

            if use_filtering and user_query and candidates:
                print(f"   Batch evaluating {len(candidates)} candidates...")
                llm = LLMInterface(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
                relevance_results = llm.batch_evaluate_relevance(user_query, candidates)

                for email, relevance in zip(candidates, relevance_results):
                    if not relevance.get("is_relevant", False) or relevance.get("score", 0) < 0.5:
                        filtered_out_count += 1
                        self.filtered_emails_log.append({
                            "subject": email["subject"],
                            "sender": email["sender"],
                            "reason": relevance.get("reason", "Not relevant"),
                            "score": relevance.get("score", 0)
                        })
                        print(f"   ⊗ Filtered: {email['subject'][:50]} (Score: {relevance.get('score', 0):.2f})")
                    else:
                        print(f"   ✓ Relevant: {email['subject'][:50]} (Score: {relevance.get('score', 0):.2f})")

                        # Process attachments for relevant emails
                        try:
                            dt = parsedate_to_datetime(email['date'])
                            formatted_date = dt.strftime("%Y%m%d")
                        except Exception:
                            formatted_date = datetime.now().strftime("%Y%m%d")

                        clean_sender = self._sanitize_filename(email['sender'].split('<')[0])[:15]
                        clean_subject = self._sanitize_filename(email['subject'])[:30]

                        attachments = []
                        payload = email.get('payload', {})
                        if 'parts' in payload:
                            for part in payload['parts']:
                                if part.get('filename'):
                                    original_filename = part['filename']
                                    if original_filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx')):
                                        if require_attachments and 'attachmentId' in part['body']:
                                            _, ext = os.path.splitext(original_filename)
                                            new_filename = f"{formatted_date}_{clean_sender}_{clean_subject}{ext}"
                                            filepath = self._download_attachment(email['id'], part['body']['attachmentId'], new_filename)
                                            if filepath:
                                                attachments.append({"filename": new_filename, "filepath": filepath})
                                                files_downloaded += 1

                        email_results.append({
                            "id": email['id'],
                            "subject": email['subject'],
                            "sender": email['sender'],
                            "date": email['date'],
                            "body": email['body'],
                            "attachments": attachments
                        })
            else:
                # No filtering - process all emails
                for email in candidates:
                    try:
                        dt = parsedate_to_datetime(email['date'])
                        formatted_date = dt.strftime("%Y%m%d")
                    except Exception:
                        formatted_date = datetime.now().strftime("%Y%m%d")

                    clean_sender = self._sanitize_filename(email['sender'].split('<')[0])[:15]
                    clean_subject = self._sanitize_filename(email['subject'])[:30]

                    attachments = []
                    payload = email.get('payload', {})
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part.get('filename'):
                                original_filename = part['filename']
                                if original_filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx')):
                                    if require_attachments and 'attachmentId' in part['body']:
                                        _, ext = os.path.splitext(original_filename)
                                        new_filename = f"{formatted_date}_{clean_sender}_{clean_subject}{ext}"
                                        filepath = self._download_attachment(email['id'], part['body']['attachmentId'], new_filename)
                                        if filepath:
                                            attachments.append({"filename": new_filename, "filepath": filepath})
                                            files_downloaded += 1

                    email_results.append({
                        "id": email['id'],
                        "subject": email['subject'],
                        "sender": email['sender'],
                        "date": email['date'],
                        "body": email['body'],
                        "attachments": attachments
                    })
            
            if self.filtered_emails_log:
                print(f"\n   📋 Filtered Out Emails Log:")
                for i, filtered in enumerate(self.filtered_emails_log[:5], 1):
                    print(f"      {i}. {filtered['subject'][:40]} - {filtered['reason'][:60]}")
                if len(self.filtered_emails_log) > 5:
                    print(f"      ... and {len(self.filtered_emails_log) - 5} more")
            
            return {
                "success": True,
                "emails_found": len(messages),
                "filtered_count": len(email_results),
                "filtered_out": filtered_out_count,
                "files_downloaded": files_downloaded,
                "filtered_log": self.filtered_emails_log,
                "results": email_results
            }
        
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}


def scan_emails(date_from: str,
                date_to: str,
                user_query: Optional[str] = None,
                user_email: Optional[str] = None,
                max_results: int = 50,
                require_attachments: bool = True,
                use_filtering: bool = True,
                inbox_category: str = "primary",
                days: int = None) -> Dict:
    scanner = EmailScanner()
    return scanner.scan(
        date_from=date_from,
        date_to=date_to,
        user_query=user_query,
        user_email=user_email,
        max_results=max_results,
        require_attachments=require_attachments,
        use_filtering=use_filtering,
        inbox_category=inbox_category,
        days=days
    )