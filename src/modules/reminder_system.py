import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)


class ReminderSystem:
    """Send bill reminder notifications via Email, Telegram, or WhatsApp"""

    def __init__(
        self,
        email_address: str = "",
        email_password: str = "",
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        telegram_bot_token: str = "",
        telegram_chat_id: str = "",
        twilio_account_sid: str = "",
        twilio_auth_token: str = "",
        twilio_from_number: str = "",
        twilio_to_number: str = ""
    ):
        """
        Initialize Reminder System

        Args:
            email_address: Sender email address
            email_password: Email app password (not regular password!)
            smtp_server: SMTP server address
            smtp_port: SMTP port
            telegram_bot_token: Telegram Bot API token
            telegram_chat_id: Telegram chat ID to send messages to
            twilio_account_sid: Twilio Account SID
            twilio_auth_token: Twilio Auth Token
            twilio_from_number: Twilio WhatsApp sender number (whatsapp:+14155238886)
            twilio_to_number: Recipient WhatsApp number (whatsapp:+1234567890)
        """
        # Email settings
        self.email_address = email_address
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

        # Telegram settings
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

        # Twilio/WhatsApp settings
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_from_number = twilio_from_number
        self.twilio_to_number = twilio_to_number
    
    def create_reminders(
        self,
        bill_id: str,
        bill_data: Dict,
        days_before: List[int] = [3, 1]
    ) -> Dict:
        """
        Create reminders for a bill
        
        Args:
            bill_id: Bill UUID
            bill_data: Bill information (vendor, amount, due_date)
            days_before: Days before due date to send reminders
            
        Returns:
            Dict with created reminders
        """
        try:
            # Parse due date
            due_date_str = bill_data.get('due_date')
            if not due_date_str:
                return {
                    "success": False,
                    "error": "No due_date provided",
                    "reminders_created": 0
                }
            
            if isinstance(due_date_str, str):
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            else:
                due_date = due_date_str
            
            # Create reminder schedule
            reminders = []
            for days in days_before:
                reminder_date = due_date - timedelta(days=days)
                
                reminders.append({
                    'bill_id': bill_id,
                    'reminder_date': reminder_date.isoformat(),
                    'days_before': days,
                    'vendor': bill_data.get('vendor', 'Unknown'),
                    'amount': bill_data.get('amount', 0.0),
                    'due_date': due_date.isoformat()
                })
            
            return {
                "success": True,
                "reminders_created": len(reminders),
                "reminders": reminders
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reminders_created": 0
            }
    
    def send_reminder(
        self,
        recipient_email: str,
        reminder_data: Dict,
        method: str = "email"
    ) -> Dict:
        """
        Send a bill reminder notification
        
        Args:
            recipient_email: Email address to send to
            reminder_data: Reminder information
            method: Notification method - "email" or "console"
            
        Returns:
            Dict with send result
        """
        if method == "console":
            return self._send_console_reminder(reminder_data)
        elif method == "email":
            return self._send_email_reminder(recipient_email, reminder_data)
        else:
            return {
                "success": False,
                "error": f"Unknown method: {method}"
            }
    
    def _send_email_reminder(self, recipient_email: str, reminder_data: Dict) -> Dict:
        """Send email reminder"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_address
            msg['To'] = recipient_email
            msg['Subject'] = f"Bill Reminder: {reminder_data.get('vendor', 'Bill')} Due Soon"
            
            # Create email body
            vendor = reminder_data.get('vendor', 'Unknown')
            amount = reminder_data.get('amount', 0.0)
            due_date = reminder_data.get('due_date', 'Unknown')
            days_before = reminder_data.get('days_before', 0)
            
            # Parse due date for better formatting
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    due_date_formatted = due_dt.strftime("%B %d, %Y")
                else:
                    due_date_formatted = due_date
            except:
                due_date_formatted = due_date
            
            # Plain text version
            text = f"""
Bill Payment Reminder

Vendor: {vendor}
Amount: ${amount:.2f}
Due Date: {due_date_formatted}

This bill is due in {days_before} day(s). Please make sure to pay on time to avoid late fees.

---
Bill Tracker Agent
"""
            
            # HTML version
            html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <h2 style="color: #dc3545;">⏰ Bill Payment Reminder</h2>
        
        <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <p><strong>Vendor:</strong> {vendor}</p>
            <p><strong>Amount:</strong> <span style="font-size: 1.2em; color: #28a745;">${amount:.2f}</span></p>
            <p><strong>Due Date:</strong> {due_date_formatted}</p>
        </div>
        
        <p style="color: #6c757d;">
            ⚠️ This bill is due in <strong>{days_before} day(s)</strong>. 
            Please make sure to pay on time to avoid late fees.
        </p>
        
        <hr style="border: 1px solid #dee2e6; margin: 20px 0;">
        
        <p style="font-size: 0.9em; color: #6c757d; text-align: center;">
            Bill Tracker Agent<br>
            Automated Reminder System
        </p>
    </div>
</body>
</html>
"""
            
            # Attach both versions
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            return {
                "success": True,
                "message": f"Reminder sent to {recipient_email}",
                "method": "email"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "email"
            }
    
    def _send_console_reminder(self, reminder_data: Dict) -> Dict:
        """Print reminder to console (for testing)"""
        try:
            vendor = reminder_data.get('vendor', 'Unknown')
            amount = reminder_data.get('amount', 0.0)
            due_date = reminder_data.get('due_date', 'Unknown')
            days_before = reminder_data.get('days_before', 0)
            
            print("\n" + "="*50)
            print("📨 BILL REMINDER")
            print("="*50)
            print(f"Vendor: {vendor}")
            print(f"Amount: ${amount:.2f}")
            print(f"Due Date: {due_date}")
            print(f"Days Until Due: {days_before}")
            print("="*50 + "\n")
            
            return {
                "success": True,
                "message": "Reminder printed to console",
                "method": "console"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "console"
            }
    
    def send_batch_reminders(
        self,
        reminders: List[Dict],
        recipient_email: str,
        method: str = "email"
    ) -> Dict:
        """
        Send multiple reminders
        
        Args:
            reminders: List of reminder data
            recipient_email: Email address to send to
            method: Notification method
            
        Returns:
            Dict with batch send result
        """
        sent = 0
        failed = 0
        errors = []
        
        for reminder in reminders:
            result = self.send_reminder(recipient_email, reminder, method)
            if result["success"]:
                sent += 1
            else:
                failed += 1
                errors.append(result.get("error"))
        
        return {
            "success": failed == 0,
            "sent": sent,
            "failed": failed,
            "errors": errors if errors else None
        }

    def send_telegram_reminder(
        self,
        chat_id: Optional[str] = None,
        reminder_data: Dict = None
    ) -> Dict:
        """
        Send reminder via Telegram Bot API

        Args:
            chat_id: Telegram chat ID (uses default if not provided)
            reminder_data: Reminder information

        Returns:
            Dict with send result
        """
        if not reminder_data:
            return {"success": False, "error": "No reminder data provided", "method": "telegram"}

        # Use provided chat_id or default
        target_chat_id = chat_id or self.telegram_chat_id

        if not self.telegram_bot_token:
            return {
                "success": False,
                "error": "TELEGRAM_BOT_TOKEN not configured",
                "method": "telegram"
            }

        if not target_chat_id:
            return {
                "success": False,
                "error": "Telegram chat_id not provided",
                "method": "telegram"
            }

        try:
            vendor = reminder_data.get('vendor', 'Unknown')
            amount = reminder_data.get('amount', 0.0)
            due_date = reminder_data.get('due_date', 'Unknown')
            days_before = reminder_data.get('days_before', 0)

            # Format due date
            try:
                if isinstance(due_date, str) and due_date != 'Unknown':
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    due_date_formatted = due_dt.strftime("%B %d, %Y")
                else:
                    due_date_formatted = str(due_date)
            except Exception:
                due_date_formatted = str(due_date)

            # Create Telegram message with Markdown
            message = f"""🔔 *Bill Payment Reminder*

*Vendor:* {vendor}
*Amount:* ${amount:.2f}
*Due Date:* {due_date_formatted}
*Days Until Due:* {days_before}

⚠️ Please ensure timely payment to avoid late fees!

_Bill Tracker Agent_"""

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }, timeout=10)

            if response.ok:
                result = response.json()
                if result.get("ok"):
                    return {
                        "success": True,
                        "message": f"Telegram reminder sent to chat {target_chat_id}",
                        "method": "telegram",
                        "message_id": result.get("result", {}).get("message_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("description", "Unknown Telegram error"),
                        "method": "telegram"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Telegram API error: {response.status_code} - {response.text}",
                    "method": "telegram"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Telegram API request timed out",
                "method": "telegram"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "telegram"
            }

    def send_whatsapp_reminder(
        self,
        to_number: Optional[str] = None,
        reminder_data: Dict = None
    ) -> Dict:
        """
        Send reminder via Twilio WhatsApp API

        Args:
            to_number: WhatsApp number (uses default if not provided)
            reminder_data: Reminder information

        Returns:
            Dict with send result
        """
        if not reminder_data:
            return {"success": False, "error": "No reminder data provided", "method": "whatsapp"}

        # Use provided number or default
        target_number = to_number or self.twilio_to_number

        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_number]):
            return {
                "success": False,
                "error": "Twilio credentials not fully configured (need SID, token, and from_number)",
                "method": "whatsapp"
            }

        if not target_number:
            return {
                "success": False,
                "error": "WhatsApp recipient number not provided",
                "method": "whatsapp"
            }

        try:
            vendor = reminder_data.get('vendor', 'Unknown')
            amount = reminder_data.get('amount', 0.0)
            due_date = reminder_data.get('due_date', 'Unknown')
            days_before = reminder_data.get('days_before', 0)

            # Format due date
            try:
                if isinstance(due_date, str) and due_date != 'Unknown':
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    due_date_formatted = due_dt.strftime("%B %d, %Y")
                else:
                    due_date_formatted = str(due_date)
            except Exception:
                due_date_formatted = str(due_date)

            # Create WhatsApp message
            message_body = f"""📋 *Bill Payment Reminder*

*Vendor:* {vendor}
*Amount:* ${amount:.2f}
*Due Date:* {due_date_formatted}
*Days Until Due:* {days_before}

⚠️ Please pay on time to avoid late fees.

_Bill Tracker Agent_"""

            # Use Twilio REST API directly (no SDK dependency)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"

            # Ensure numbers have whatsapp: prefix
            from_num = self.twilio_from_number if self.twilio_from_number.startswith("whatsapp:") else f"whatsapp:{self.twilio_from_number}"
            to_num = target_number if target_number.startswith("whatsapp:") else f"whatsapp:{target_number}"

            response = requests.post(
                url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                data={
                    "From": from_num,
                    "To": to_num,
                    "Body": message_body
                },
                timeout=15
            )

            if response.ok:
                result = response.json()
                return {
                    "success": True,
                    "message": f"WhatsApp reminder sent to {target_number}",
                    "method": "whatsapp",
                    "sid": result.get("sid")
                }
            else:
                error_data = response.json() if response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("message", f"Twilio error: {response.status_code}"),
                    "method": "whatsapp"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Twilio API request timed out",
                "method": "whatsapp"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "whatsapp"
            }

    def get_available_channels(self) -> List[str]:
        """
        Get list of configured notification channels

        Returns:
            List of available channel names
        """
        channels = ["console"]  # Always available

        if self.email_address and self.email_password:
            channels.append("email")

        if self.telegram_bot_token and self.telegram_chat_id:
            channels.append("telegram")

        if all([self.twilio_account_sid, self.twilio_auth_token,
                self.twilio_from_number, self.twilio_to_number]):
            channels.append("whatsapp")

        return channels

    def test_channel(self, channel: str) -> Dict:
        """
        Send a test message to verify channel configuration

        Args:
            channel: Channel to test (email, telegram, whatsapp, console)

        Returns:
            Dict with test result
        """
        test_data = {
            'vendor': 'Test Vendor',
            'amount': 99.99,
            'due_date': datetime.now().isoformat(),
            'days_before': 1
        }

        if channel == "email":
            return self.send_reminder(self.email_address, test_data, method="email")
        elif channel == "telegram":
            return self.send_telegram_reminder(reminder_data=test_data)
        elif channel == "whatsapp":
            return self.send_whatsapp_reminder(reminder_data=test_data)
        elif channel == "console":
            return self.send_reminder("", test_data, method="console")
        else:
            return {"success": False, "error": f"Unknown channel: {channel}"}

    def send_whatsapp_message(
        self,
        message: str,
        to_number: Optional[str] = None
    ) -> Dict:
        """
        Send a generic WhatsApp message (for AI responses, not just reminders)

        Args:
            message: The message text to send
            to_number: WhatsApp number (uses default if not provided)

        Returns:
            Dict with send result
        """
        if not message:
            return {"success": False, "error": "No message provided", "method": "whatsapp"}

        # Use provided number or default
        target_number = to_number or self.twilio_to_number

        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_number]):
            return {
                "success": False,
                "error": "Twilio credentials not fully configured (need SID, token, and from_number)",
                "method": "whatsapp"
            }

        if not target_number:
            return {
                "success": False,
                "error": "WhatsApp recipient number not provided",
                "method": "whatsapp"
            }

        try:
            # Use Twilio REST API directly (no SDK dependency)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"

            # Ensure numbers have whatsapp: prefix
            from_num = self.twilio_from_number if self.twilio_from_number.startswith("whatsapp:") else f"whatsapp:{self.twilio_from_number}"
            to_num = target_number if target_number.startswith("whatsapp:") else f"whatsapp:{target_number}"

            # Twilio WhatsApp sandbox has 1600 char limit
            # Production accounts have higher limits (~65536)
            MAX_LENGTH = 1550  # Leave buffer for safety
            if len(message) > MAX_LENGTH:
                message = message[:MAX_LENGTH - 50] + "\n\n... (truncated)"

            response = requests.post(
                url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                data={
                    "From": from_num,
                    "To": to_num,
                    "Body": message
                },
                timeout=15
            )

            if response.ok:
                result = response.json()
                return {
                    "success": True,
                    "message": f"WhatsApp message sent to {target_number}",
                    "method": "whatsapp",
                    "sid": result.get("sid")
                }
            else:
                error_data = response.json() if response.text else {}
                return {
                    "success": False,
                    "error": error_data.get("message", f"Twilio error: {response.status_code}"),
                    "method": "whatsapp"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Twilio API request timed out",
                "method": "whatsapp"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "whatsapp"
            }

    def send_telegram_message(
        self,
        message: str,
        chat_id: Optional[str] = None
    ) -> Dict:
        """
        Send a generic Telegram message (for AI responses, not just reminders)

        Args:
            message: The message text to send
            chat_id: Telegram chat ID (uses default if not provided)

        Returns:
            Dict with send result
        """
        if not message:
            return {"success": False, "error": "No message provided", "method": "telegram"}

        target_chat_id = chat_id or self.telegram_chat_id

        if not self.telegram_bot_token:
            return {
                "success": False,
                "error": "TELEGRAM_BOT_TOKEN not configured",
                "method": "telegram"
            }

        if not target_chat_id:
            return {
                "success": False,
                "error": "Telegram chat_id not provided",
                "method": "telegram"
            }

        try:
            # Truncate if too long (Telegram limit is 4096)
            if len(message) > 4000:
                message = message[:3950] + "\n\n... (message truncated)"

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }, timeout=10)

            if response.ok:
                result = response.json()
                if result.get("ok"):
                    return {
                        "success": True,
                        "message": f"Telegram message sent to chat {target_chat_id}",
                        "method": "telegram",
                        "message_id": result.get("result", {}).get("message_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("description", "Unknown Telegram error"),
                        "method": "telegram"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Telegram API error: {response.status_code} - {response.text}",
                    "method": "telegram"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Telegram API request timed out",
                "method": "telegram"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "telegram"
            }