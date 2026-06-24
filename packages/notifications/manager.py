from __future__ import annotations

import sqlite3
import time
from datetime import date, timedelta
from typing import Optional

from loguru import logger

from packages.notifications.base import (
    NotificationCategory,
    NotificationChannel,
    NotificationLevel,
    NotificationPayload,
    SendResult,
)


CHANNEL_CLASSES = {}

try:
    from packages.notifications.telegram import TelegramChannel

    CHANNEL_CLASSES["telegram"] = TelegramChannel
except ImportError:
    TelegramChannel = None


class NotificationManager:
    def __init__(self, channels: list[NotificationChannel], db_path: str = "data/applications.db"):
        self.channels = channels
        self.db_path = db_path
        self._init_db()

    @classmethod
    def from_config(cls, config: dict, db_path: str = "data/applications.db") -> "NotificationManager":
        notif_cfg = config.get("notifications", {}) or {}
        if not notif_cfg.get("enabled", False):
            return cls([], db_path=db_path)
        channels = []
        for channel_name, channel_cfg in (notif_cfg.get("channels", {}) or {}).items():
            channel_cls = CHANNEL_CLASSES.get(channel_name)
            if not channel_cls:
                logger.warning(f"Unknown notification channel: {channel_name}")
                continue
            try:
                channels.append(channel_cls(channel_cfg))
            except Exception as exc:
                logger.warning(f"Notification channel init failed for {channel_name}: {exc}")
        return cls(channels, db_path=db_path)

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
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
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.debug(f"Notification table init failed: {exc}")

    def send(self, payload: NotificationPayload) -> dict[str, SendResult]:
        results: dict[str, SendResult] = {}
        for channel in self.channels:
            if not channel.should_send(payload):
                continue
            try:
                result = channel.send(payload)
                results[channel.name] = result
                self._log_send(channel.name, payload, result)
            except Exception as exc:
                results[channel.name] = SendResult(success=False, channel=channel.name, error=str(exc))
        return results

    def _log_send(self, channel_name: str, payload: NotificationPayload, result: SendResult):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT INTO notification_log
                (timestamp, date, channel, title, category, level, success, duration_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    date.today().strftime("%Y-%m-%d"),
                    channel_name,
                    payload.title,
                    payload.category.value,
                    payload.level.value,
                    1 if result.success else 0,
                    result.duration_ms,
                    result.error or None,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.debug(f"Notification log write failed: {exc}")

    def test_all(self) -> dict[str, tuple[bool, str]]:
        results = {}
        for channel in self.channels:
            if channel.enabled:
                results[channel.name] = channel.test_connection()
        return results

    def get_stats(self, days: int = 7) -> dict:
        try:
            since = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                """
                SELECT channel, COUNT(*) AS total, SUM(success) AS success, AVG(duration_ms) AS avg_ms
                FROM notification_log
                WHERE date >= ?
                GROUP BY channel
                """,
                (since,),
            ).fetchall()
            conn.close()
            return {
                "since": since,
                "channels": [
                    {
                        "channel": row[0],
                        "total": row[1],
                        "success": row[2] or 0,
                        "avg_ms": int(row[3] or 0),
                    }
                    for row in rows
                ],
            }
        except Exception as exc:
            return {"error": str(exc)}


def notify(
    manager: Optional[NotificationManager],
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    category: NotificationCategory = NotificationCategory.BOT_STATE,
    metadata: Optional[dict] = None,
) -> None:
    if manager is None:
        return
    manager.send(
        NotificationPayload(
            title=title,
            message=message,
            level=level,
            category=category,
            metadata=metadata,
        )
    )
