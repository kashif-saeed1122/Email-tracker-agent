from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import base64
from typing import Dict, List
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class EmailScanner:
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.download_dir = "data/raw/attachments"
        os.makedirs(self.download_dir, exist_ok=True)
    
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
    
    def _check_content_relevance(self, text: str, keywords: List[str]) -> str:
        if not keywords:
            return "HIGH"
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches >= 2: return "HIGH"
        elif matches >= 1: return "MEDIUM"
        return "LOW"
    
    def _sanitize_filename(self, text: str) -> str:
        """Helper to create safe filenames from email subjects/senders"""
        # Keep only alphanumeric and spaces, replace spaces with underscores
        safe = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return re.sub(r'\s+', '_', safe.strip())

    def _download_attachment(self, message_id: str, attachment_id: str, filename: str) -> str:
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            filepath = os.path.join(self.download_dir, filename)
            
            # Handle duplicates
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
    
    def scan(self, date_from: str, date_to: str, keywords: List[str], max_results: int = 50, require_attachments: bool = True, use_filtering: bool = True) -> Dict:
        
        if not self.service:
            self.authenticate()
        
        keyword_query = ' OR '.join([f'"{k}"' for k in keywords]) if keywords else ""
        query = f'after:{date_from} before:{date_to}'
        if require_attachments: query += ' has:attachment'
        if keyword_query: query += f' ({keyword_query})'
        
        print(f"Searching Gmail: {query}")
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return {"success": True, "emails_found": 0, "results": []}
            
            email_results = []
            files_downloaded = 0
            
            for msg in messages:
                message = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = message['payload']['headers']
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No_Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                body = self._get_message_body(message['payload'])
                
                # Check Relevance
                if use_filtering and keywords:
                    if self._check_content_relevance(subject, keywords) == "LOW" and \
                       self._check_content_relevance(body, keywords) == "LOW":
                        continue
                
                # --- NEW NAMING LOGIC STARTS HERE ---
                try:
                    # Parse date to YYYY-MM-DD
                    dt = parsedate_to_datetime(date_str)
                    formatted_date = dt.strftime("%Y%m%d")
                except:
                    formatted_date = datetime.now().strftime("%Y%m%d")

                # Clean Sender (remove <email>) and Subject
                clean_sender = self._sanitize_filename(sender.split('<')[0])[:15]
                clean_subject = self._sanitize_filename(subject)[:30]
                # -------------------------------------

                attachments = []
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if part.get('filename'):
                            original_filename = part['filename']
                            if original_filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx')):
                                if require_attachments and 'attachmentId' in part['body']:
                                    
                                    # Create Custom Filename: 20240101_Sender_Subject_OriginalName.pdf
                                    _, ext = os.path.splitext(original_filename)
                                    new_filename = f"{formatted_date}_{clean_sender}_{clean_subject}{ext}"
                                    
                                    filepath = self._download_attachment(msg['id'], part['body']['attachmentId'], new_filename)
                                    
                                    if filepath:
                                        attachments.append({"filename": new_filename, "filepath": filepath})
                                        files_downloaded += 1

                email_results.append({
                    "id": msg['id'],
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "body": body[:2000],
                    "attachments": attachments
                })
            
            return {
                "success": True,
                "emails_found": len(messages),
                "filtered_count": len(email_results),
                "files_downloaded": files_downloaded,
                "results": email_results
            }
        
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}

def scan_emails(date_from: str, date_to: str, keywords: List[str], max_results: int = 50, require_attachments: bool = True, use_filtering: bool = True) -> Dict:
    scanner = EmailScanner()
    return scanner.scan(date_from, date_to, keywords, max_results, require_attachments, use_filtering)