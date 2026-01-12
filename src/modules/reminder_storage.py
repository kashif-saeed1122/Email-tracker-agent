"""
Reminder Storage Module
Persistent SQLite storage for bill reminders and their scheduling status.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import os


class ReminderStorage:
    """Persistent storage for reminders using SQLite"""

    def __init__(self, db_path: str = "data/reminders.db"):
        """
        Initialize Reminder Storage

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create reminders table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                bill_id TEXT,
                vendor TEXT,
                amount REAL,
                due_date TEXT,
                reminder_date TEXT,
                days_before INTEGER,
                status TEXT DEFAULT 'pending',
                channel TEXT DEFAULT 'email',
                recipient TEXT,
                created_at TEXT,
                sent_at TEXT,
                error_message TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminder_date ON reminders(reminder_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON reminders(status)
        """)
        conn.commit()
        conn.close()

    def add_reminder(self, reminder: Dict) -> str:
        """
        Store a new reminder

        Args:
            reminder: Reminder data dict containing:
                - bill_id: ID of the associated bill
                - vendor: Vendor name
                - amount: Bill amount
                - due_date: Bill due date (ISO format)
                - reminder_date: When to send reminder (ISO format)
                - days_before: Days before due date
                - channel: Notification channel (email, telegram, whatsapp)
                - recipient: Recipient address/ID

        Returns:
            str: Generated reminder ID
        """
        reminder_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO reminders
            (id, bill_id, vendor, amount, due_date, reminder_date, days_before,
             status, channel, recipient, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            reminder_id,
            reminder.get('bill_id', ''),
            reminder.get('vendor', 'Unknown'),
            reminder.get('amount', 0.0),
            reminder.get('due_date', ''),
            reminder.get('reminder_date', ''),
            reminder.get('days_before', 0),
            reminder.get('channel', 'email'),
            reminder.get('recipient', ''),
            created_at
        ))
        conn.commit()
        conn.close()

        return reminder_id

    def get_due_reminders(self) -> List[Dict]:
        """
        Get all reminders that are due now or overdue (pending status)

        Returns:
            List of reminder dicts
        """
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending'
            AND reminder_date <= ?
            ORDER BY reminder_date ASC
        """, (now,))

        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return reminders

    def get_pending_reminders(self) -> List[Dict]:
        """
        Get all pending reminders (not yet sent)

        Returns:
            List of reminder dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending'
            ORDER BY reminder_date ASC
        """)

        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return reminders

    def mark_sent(self, reminder_id: str) -> bool:
        """
        Mark a reminder as sent

        Args:
            reminder_id: ID of the reminder

        Returns:
            bool: Success status
        """
        sent_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            UPDATE reminders
            SET status = 'sent', sent_at = ?
            WHERE id = ?
        """, (sent_at, reminder_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def mark_failed(self, reminder_id: str, error_message: str) -> bool:
        """
        Mark a reminder as failed

        Args:
            reminder_id: ID of the reminder
            error_message: Error description

        Returns:
            bool: Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            UPDATE reminders
            SET status = 'failed', error_message = ?
            WHERE id = ?
        """, (error_message, reminder_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def get_pending_for_bill(self, bill_id: str) -> List[Dict]:
        """
        Get all pending reminders for a specific bill

        Args:
            bill_id: Bill ID

        Returns:
            List of reminder dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM reminders
            WHERE bill_id = ? AND status = 'pending'
            ORDER BY reminder_date ASC
        """, (bill_id,))

        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return reminders

    def delete_reminder(self, reminder_id: str) -> bool:
        """
        Delete a reminder

        Args:
            reminder_id: ID of the reminder

        Returns:
            bool: Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            DELETE FROM reminders WHERE id = ?
        """, (reminder_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def delete_reminders_for_bill(self, bill_id: str) -> int:
        """
        Delete all reminders for a specific bill

        Args:
            bill_id: Bill ID

        Returns:
            int: Number of deleted reminders
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            DELETE FROM reminders WHERE bill_id = ?
        """, (bill_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected

    def get_stats(self) -> Dict:
        """
        Get reminder statistics

        Returns:
            Dict with counts by status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM reminders
            GROUP BY status
        """)

        stats = {"pending": 0, "sent": 0, "failed": 0, "total": 0}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
            stats["total"] += row[1]

        conn.close()
        return stats

    def get_upcoming_reminders(self, hours: int = 24) -> List[Dict]:
        """
        Get reminders due in the next N hours

        Args:
            hours: Number of hours to look ahead

        Returns:
            List of reminder dicts
        """
        from datetime import timedelta
        now = datetime.now()
        future = (now + timedelta(hours=hours)).isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending'
            AND reminder_date >= ?
            AND reminder_date <= ?
            ORDER BY reminder_date ASC
        """, (now.isoformat(), future))

        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return reminders

    def cleanup_old_reminders(self, days: int = 30) -> int:
        """
        Delete old sent/failed reminders

        Args:
            days: Delete reminders older than this many days

        Returns:
            int: Number of deleted reminders
        """
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            DELETE FROM reminders
            WHERE status IN ('sent', 'failed')
            AND created_at < ?
        """, (cutoff,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected
