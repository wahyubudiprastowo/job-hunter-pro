from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


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
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


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
        self.enabled = bool(self.config.get("enabled", False))
        self.categories = set(self.config.get("categories", []))
        self.min_level = str(self.config.get("min_level", "info") or "info")

    def should_send(self, payload: NotificationPayload) -> bool:
        if not self.enabled:
            return False
        if self.categories and payload.category.value not in self.categories:
            return False
        levels = ["info", "success", "warning", "error", "critical"]
        try:
            return levels.index(payload.level.value) >= levels.index(self.min_level)
        except ValueError:
            return True

    @abstractmethod
    def send(self, payload: NotificationPayload) -> SendResult:
        raise NotImplementedError

    def test_connection(self) -> tuple[bool, str]:
        payload = NotificationPayload(
            title="Test notification",
            message="If you see this, notifications are working.",
            level=NotificationLevel.INFO,
            category=NotificationCategory.BOT_STATE,
        )
        result = self.send(payload)
        return result.success, result.error or "OK"
