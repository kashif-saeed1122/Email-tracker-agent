"""
Reminder Scheduler Module
Background scheduler for checking and sending due reminders.
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable
import logging

from src.modules.reminder_storage import ReminderStorage
from src.modules.reminder_system import ReminderSystem


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Background scheduler for checking and sending due reminders"""

    def __init__(
        self,
        storage: ReminderStorage,
        sender: ReminderSystem,
        check_interval: int = 300,  # 5 minutes default
        on_reminder_sent: Optional[Callable] = None,
        on_reminder_failed: Optional[Callable] = None
    ):
        """
        Initialize Reminder Scheduler

        Args:
            storage: ReminderStorage instance for persistence
            sender: ReminderSystem instance for sending notifications
            check_interval: Seconds between reminder checks (default: 300 = 5 min)
            on_reminder_sent: Optional callback when reminder is sent
            on_reminder_failed: Optional callback when reminder fails
        """
        self.storage = storage
        self.sender = sender
        self.check_interval = check_interval
        self.on_reminder_sent = on_reminder_sent
        self.on_reminder_failed = on_reminder_failed

        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Reminder scheduler started (checking every %d seconds)", self.check_interval)

    def stop(self, timeout: float = 5.0):
        """
        Stop the scheduler

        Args:
            timeout: Maximum seconds to wait for thread to stop
        """
        if not self.running:
            return

        self.running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("Scheduler thread did not stop cleanly")
            else:
                logger.info("Reminder scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        while self.running and not self._stop_event.is_set():
            try:
                self._check_and_send_due_reminders()
            except Exception as e:
                logger.error("Scheduler error: %s", str(e))

            # Wait for interval or stop event
            self._stop_event.wait(timeout=self.check_interval)

        logger.info("Scheduler loop ended")

    def _check_and_send_due_reminders(self):
        """Check for due reminders and send them"""
        due_reminders = self.storage.get_due_reminders()

        if not due_reminders:
            return

        logger.info("Found %d due reminders", len(due_reminders))

        for reminder in due_reminders:
            self._send_reminder(reminder)

    def _send_reminder(self, reminder: dict):
        """
        Send a single reminder

        Args:
            reminder: Reminder dict from storage
        """
        reminder_id = reminder.get('id')
        channel = reminder.get('channel', 'email')
        recipient = reminder.get('recipient', '')

        reminder_data = {
            'vendor': reminder.get('vendor', 'Unknown'),
            'amount': reminder.get('amount', 0.0),
            'due_date': reminder.get('due_date', ''),
            'days_before': reminder.get('days_before', 0)
        }

        logger.info("Sending reminder for %s via %s", reminder_data['vendor'], channel)

        try:
            # Send based on channel
            if channel == 'email':
                result = self.sender.send_reminder(recipient, reminder_data, method='email')
            elif channel == 'telegram':
                result = self.sender.send_telegram_reminder(recipient, reminder_data)
            elif channel == 'whatsapp':
                result = self.sender.send_whatsapp_reminder(recipient, reminder_data)
            elif channel == 'console':
                result = self.sender.send_reminder(recipient, reminder_data, method='console')
            else:
                result = {'success': False, 'error': f'Unknown channel: {channel}'}

            if result.get('success'):
                self.storage.mark_sent(reminder_id)
                logger.info("Reminder sent successfully for %s", reminder_data['vendor'])

                if self.on_reminder_sent:
                    self.on_reminder_sent(reminder, result)
            else:
                error_msg = result.get('error', 'Unknown error')
                self.storage.mark_failed(reminder_id, error_msg)
                logger.error("Failed to send reminder for %s: %s", reminder_data['vendor'], error_msg)

                if self.on_reminder_failed:
                    self.on_reminder_failed(reminder, result)

        except Exception as e:
            error_msg = str(e)
            self.storage.mark_failed(reminder_id, error_msg)
            logger.error("Exception sending reminder: %s", error_msg)

            if self.on_reminder_failed:
                self.on_reminder_failed(reminder, {'success': False, 'error': error_msg})

    def check_now(self) -> dict:
        """
        Manually trigger a check (for testing or immediate processing)

        Returns:
            Dict with results of the check
        """
        due_reminders = self.storage.get_due_reminders()
        sent = 0
        failed = 0

        for reminder in due_reminders:
            reminder_id = reminder.get('id')
            channel = reminder.get('channel', 'email')
            recipient = reminder.get('recipient', '')

            reminder_data = {
                'vendor': reminder.get('vendor', 'Unknown'),
                'amount': reminder.get('amount', 0.0),
                'due_date': reminder.get('due_date', ''),
                'days_before': reminder.get('days_before', 0)
            }

            try:
                if channel == 'email':
                    result = self.sender.send_reminder(recipient, reminder_data, method='email')
                elif channel == 'telegram':
                    result = self.sender.send_telegram_reminder(recipient, reminder_data)
                elif channel == 'whatsapp':
                    result = self.sender.send_whatsapp_reminder(recipient, reminder_data)
                else:
                    result = self.sender.send_reminder(recipient, reminder_data, method='console')

                if result.get('success'):
                    self.storage.mark_sent(reminder_id)
                    sent += 1
                else:
                    self.storage.mark_failed(reminder_id, result.get('error', 'Unknown'))
                    failed += 1

            except Exception as e:
                self.storage.mark_failed(reminder_id, str(e))
                failed += 1

        return {
            'checked': len(due_reminders),
            'sent': sent,
            'failed': failed
        }

    def get_status(self) -> dict:
        """
        Get scheduler status

        Returns:
            Dict with scheduler status and stats
        """
        stats = self.storage.get_stats()
        upcoming = self.storage.get_upcoming_reminders(hours=24)

        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'stats': stats,
            'upcoming_24h': len(upcoming),
            'next_reminders': upcoming[:5]  # Show next 5 upcoming
        }


def create_scheduler(
    email_address: str,
    email_password: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    check_interval: int = 300,
    db_path: str = "data/reminders.db"
) -> ReminderScheduler:
    """
    Factory function to create a configured scheduler

    Args:
        email_address: Sender email address
        email_password: Email app password
        smtp_server: SMTP server address
        smtp_port: SMTP port
        check_interval: Seconds between checks
        db_path: Path to reminder database

    Returns:
        Configured ReminderScheduler instance
    """
    storage = ReminderStorage(db_path=db_path)
    sender = ReminderSystem(
        email_address=email_address,
        email_password=email_password,
        smtp_server=smtp_server,
        smtp_port=smtp_port
    )

    return ReminderScheduler(
        storage=storage,
        sender=sender,
        check_interval=check_interval
    )
