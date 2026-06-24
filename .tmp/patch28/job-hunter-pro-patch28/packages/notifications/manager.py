"""Notification Manager (Patch 28) - orchestrates multiple channels."""
from __future__ import annotations
import sqlite3
import time
from typing import Dict, List, Optional
from datetime import date, datetime
from loguru import logger

from packages.notifications.base import (
    NotificationChannel,
    NotificationPayload,
    NotificationLevel,
    NotificationCategory,
    SendResult,
)


CHANNEL_CLASSES = {}

try:
    from packages.notifications.telegram import TelegramChannel
    CHANNEL_CLASSES["telegram"] = TelegramChannel
except ImportError:
    pass


class NotificationManager:
    """Manages multiple notification channels."""

    def __init__(self, channels: List[NotificationChannel], db_path: str = "data/applications.db"):
        self.channels = channels
        self.db_path = db_path
        self._init_db()
        enabled_count = sum(1 for c in channels if c.enabled)
        logger.info(f"📡 NotificationManager ready: {enabled_count}/{len(channels)} channels enabled")

    @classmethod
    def from_config(cls, config: dict, db_path: str = "data/applications.db") -> "NotificationManager":
        """Build manager from config dict (typically config.yaml notifications: section)."""
        notif_cfg = config.get("notifications", {})
        if not notif_cfg.get("enabled", False):
            logger.info("📡 Notifications globally disabled")
            return cls([], db_path=db_path)

        channels_cfg = notif_cfg.get("channels", {})
        channels = []
        for channel_name, channel_config in channels_cfg.items():
            channel_cls = CHANNEL_CLASSES.get(channel_name)
            if not channel_cls:
                logger.warning(f"Unknown channel type: {channel_name}")
                continue
            try:
                channels.append(channel_cls(channel_config))
            except Exception as e:
                logger.error(f"Failed to init {channel_name} channel: {e}")

        return cls(channels, db_path=db_path)

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    channel TEXT,
                    title TEXT,
                    category TEXT,
                    level TEXT,
                    success INTEGER,
                    duration_ms INTEGER,
                    error TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Notification table init failed: {e}")

    def send(self, payload: NotificationPayload) -> Dict[str, SendResult]:
        """Send through all eligible channels. Returns dict of channel_name -> SendResult."""
        results = {}
        for channel in self.channels:
            if channel.should_send(payload):
                try:
                    result = channel.send(payload)
                    results[channel.name] = result
                    self._log_send(channel.name, payload, result)
                    if result.success:
                        logger.debug(f"📤 Notification sent via {channel.name} ({result.duration_ms}ms)")
                    else:
                        logger.warning(f"Notification failed via {channel.name}: {result.error}")
                except Exception as e:
                    logger.error(f"Channel {channel.name} crashed: {e}")
                    results[channel.name] = SendResult(success=False, channel=channel.name, error=str(e))
        return results

    def _log_send(self, channel_name, payload, result):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO notification_log
                (timestamp, date, channel, title, category, level, success, duration_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(time.time()),
                date.today().strftime("%Y-%m-%d"),
                channel_name,
                payload.title,
                payload.category.value if hasattr(payload.category, "value") else payload.category,
                payload.level.value if hasattr(payload.level, "value") else payload.level,
                1 if result.success else 0,
                result.duration_ms,
                result.error or None,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Log send failed: {e}")

    def test_all(self) -> Dict[str, tuple]:
        """Test all enabled channels with a probe message."""
        results = {}
        for channel in self.channels:
            if channel.enabled:
                ok, msg = channel.test_connection()
                results[channel.name] = (ok, msg)
        return results

    def get_stats(self, days: int = 7) -> dict:
        """Get notification stats for last N days."""
        try:
            from datetime import timedelta
            since = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT channel, COUNT(*) as total, SUM(success) as success, AVG(duration_ms) as avg_ms
                FROM notification_log WHERE date >= ?
                GROUP BY channel
            """, (since,))
            rows = cursor.fetchall()
            conn.close()
            return {
                "since": since,
                "channels": [
                    {"channel": r[0], "total": r[1], "success": r[2] or 0, "avg_ms": int(r[3] or 0)}
                    for r in rows
                ]
            }
        except Exception as e:
            return {"error": str(e)}


def notify(manager: Optional[NotificationManager], title: str, message: str,
           level: NotificationLevel = NotificationLevel.INFO,
           category: NotificationCategory = NotificationCategory.BOT_STATE,
           metadata: Optional[dict] = None) -> None:
    """Convenience function to send notification."""
    if manager is None:
        return
    payload = NotificationPayload(
        title=title, message=message, level=level, category=category, metadata=metadata
    )
    manager.send(payload)