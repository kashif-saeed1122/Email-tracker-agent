import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime, timedelta


class ReminderSystem:
    """Send bill reminder notifications"""
    
    def __init__(
        self,
        email_address: str,
        email_password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587
    ):
        """
        Initialize Reminder System
        
        Args:
            email_address: Sender email address
            email_password: Email app password (not regular password!)
            smtp_server: SMTP server address
            smtp_port: SMTP port
        """
        self.email_address = email_address
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
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