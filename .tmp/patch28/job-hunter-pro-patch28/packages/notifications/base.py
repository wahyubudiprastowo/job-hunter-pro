"""Notification Channel Base Interface (Patch 28)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class NotificationLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationCategory(str, Enum):
    BOT_STATE = "bot_state"
    APPLY_SUCCESS = "apply_success"
    APPLY_FAILED = "apply_failed"
    RATE_LIMIT = "rate_limit"
    CAPTCHA = "captcha"
    MILESTONE = "milestone"
    DAILY_SUMMARY = "daily_summary"
    ERROR = "error"
    UNANSWERED = "unanswered"
    INTERVIEW = "interview"


@dataclass
class NotificationPayload:
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    category: NotificationCategory = NotificationCategory.BOT_STATE
    metadata: Optional[dict] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        lvl = self.level.value if isinstance(self.level, NotificationLevel) else self.level
        cat = self.category.value if isinstance(self.category, NotificationCategory) else self.category
        return {
            "title": self.title,
            "message": self.message,
            "level": lvl,
            "category": cat,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class SendResult:
    success: bool
    channel: str
    duration_ms: int = 0
    error: str = ""
    response_data: Optional[dict] = None


class NotificationChannel(ABC):
    name = "abstract"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.categories = set(self.config.get("categories", []))
        self.min_level = self.config.get("min_level", "info")

    def should_send(self, payload: NotificationPayload) -> bool:
        if not self.enabled:
            return False
        if self.categories and payload.category.value not in self.categories:
            return False
        levels_order = ["info", "success", "warning", "error", "critical"]
        try:
            payload_idx = levels_order.index(payload.level.value)
            min_idx = levels_order.index(self.min_level)
            if payload_idx < min_idx:
                return False
        except ValueError:
            pass
        return True

    @abstractmethod
    def send(self, payload: NotificationPayload) -> SendResult:
        pass

    def test_connection(self) -> tuple[bool, str]:
        payload = NotificationPayload(
            title="Test Notification",
            message="If you see this, the channel is working.",
            level=NotificationLevel.INFO,
            category=NotificationCategory.BOT_STATE,
        )
        result = self.send(payload)
        return result.success, result.error or "OK"