"""SQLite database module for subscription management."""

import sqlite3
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SubscriptionDB:
    """Manage subscriptions in SQLite database."""
    
    def __init__(self, db_path: str = "/app/data/subscriptions.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        logger.info(f"SubscriptionDB initialized at {db_path}")
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    sub_type TEXT NOT NULL,
                    sub_target TEXT NOT NULL,
                    sub_name TEXT,
                    last_check_time INTEGER,
                    last_work_id INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    UNIQUE(user_id, sub_type, sub_target)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON subscriptions(user_id)
            """)
            conn.commit()
    
    def add_subscription(
        self, 
        user_id: int, 
        sub_type: str, 
        sub_target: str, 
        sub_name: str = None
    ) -> bool:
        """Add a new subscription.
        
        Args:
            user_id: Telegram user ID
            sub_type: 'author' or 'tag'
            sub_target: Author ID or tag name
            sub_name: Display name for the subscription
            
        Returns:
            True if added successfully, False if already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO subscriptions 
                       (user_id, sub_type, sub_target, sub_name) 
                       VALUES (?, ?, ?, ?)""",
                    (user_id, sub_type, sub_target, sub_name)
                )
                conn.commit()
            logger.info(f"User {user_id} subscribed to {sub_type}:{sub_target}")
            return True
        except sqlite3.IntegrityError:
            logger.info(f"Subscription already exists: {user_id} -> {sub_type}:{sub_target}")
            return False
    
    def remove_subscription(self, user_id: int, sub_type: str, sub_target: str) -> bool:
        """Remove a subscription.
        
        Returns:
            True if removed, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """DELETE FROM subscriptions 
                   WHERE user_id = ? AND sub_type = ? AND sub_target = ?""",
                (user_id, sub_type, sub_target)
            )
            conn.commit()
            removed = cursor.rowcount > 0
            if removed:
                logger.info(f"User {user_id} unsubscribed from {sub_type}:{sub_target}")
            return removed
    
    def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all subscriptions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC""",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions (for scheduled checks)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM subscriptions")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_last_check(self, sub_id: int, last_work_id: int):
        """Update the last checked work ID for a subscription."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE subscriptions 
                   SET last_check_time = ?, last_work_id = ? 
                   WHERE id = ?""",
                (int(datetime.now().timestamp()), last_work_id, sub_id)
            )
            conn.commit()
    
    def is_subscribed(self, user_id: int, sub_type: str, sub_target: str) -> bool:
        """Check if a user is subscribed to a target."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT 1 FROM subscriptions 
                   WHERE user_id = ? AND sub_type = ? AND sub_target = ?""",
                (user_id, sub_type, sub_target)
            )
            return cursor.fetchone() is not None
    
    def get_subscription_count(self, user_id: int) -> int:
        """Get the number of subscriptions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
            return cursor.fetchone()[0]
