"""Telegram Notification Channel (Patch 28)."""
from __future__ import annotations
import os
import time
from typing import Optional
from loguru import logger

from packages.notifications.base import (
    NotificationChannel,
    NotificationPayload,
    SendResult,
)


LEVEL_EMOJI = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🚨",
}

CATEGORY_EMOJI = {
    "bot_state": "🤖",
    "apply_success": "📩",
    "apply_failed": "❌",
    "rate_limit": "🛑",
    "captcha": "🧩",
    "milestone": "🎉",
    "daily_summary": "📊",
    "error": "🐛",
    "unanswered": "❓",
    "interview": "🎤",
}


class TelegramChannel(NotificationChannel):
    name = "telegram"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "") or self.config.get("token", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "") or self.config.get("chat_id", "")
        self.parse_mode = self.config.get("parse_mode", "HTML")
        self.disable_notification = self.config.get("disable_notification", False)
        self.timeout = int(self.config.get("timeout", 15))

        if self.enabled:
            if not self.token or not self.chat_id:
                logger.warning("⚠️ Telegram channel enabled but TOKEN/CHAT_ID missing — disabling")
                self.enabled = False
            else:
                masked = self.token[:8] + "***" + self.token[-4:] if len(self.token) > 16 else "***"
                logger.success(f"📱 Telegram channel ready (chat={self.chat_id}, token={masked})")

    def send(self, payload: NotificationPayload) -> SendResult:
        if not self.enabled:
            return SendResult(success=False, channel=self.name, error="Channel disabled")

        try:
            import requests
        except ImportError:
            return SendResult(success=False, channel=self.name, error="requests not installed")

        start = time.time()
        text = self._format_message(payload)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            r = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": self.parse_mode,
                "disable_notification": self.disable_notification,
                "disable_web_page_preview": True,
            }, timeout=self.timeout)
            data = r.json()
            duration_ms = int((time.time() - start) * 1000)

            if data.get("ok"):
                return SendResult(success=True, channel=self.name, duration_ms=duration_ms, response_data=data.get("result"))
            else:
                return SendResult(success=False, channel=self.name, duration_ms=duration_ms, error=data.get("description", "Unknown error"))
        except Exception as e:
            return SendResult(success=False, channel=self.name, error=f"Send failed: {e}")

    def _format_message(self, payload: NotificationPayload) -> str:
        level_emoji = LEVEL_EMOJI.get(
            payload.level.value if hasattr(payload.level, "value") else payload.level, "ℹ️"
        )
        cat_emoji = CATEGORY_EMOJI.get(
            payload.category.value if hasattr(payload.category, "value") else payload.category, ""
        )

        if self.parse_mode == "HTML":
            lines = []
            lines.append(f"{level_emoji} <b>{self._escape_html(payload.title)}</b> {cat_emoji}")
            lines.append("")
            lines.append(self._escape_html(payload.message))
            if payload.metadata:
                lines.append("")
                lines.append("<i>Details:</i>")
                for key, value in list(payload.metadata.items())[:10]:
                    safe_key = self._escape_html(str(key))
                    safe_val = self._escape_html(str(value))
                    lines.append(f"<code>{safe_key}</code>: {safe_val}")
            if payload.timestamp:
                ts = payload.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append("")
                lines.append(f"<i>📅 {ts}</i>")
            return "\n".join(lines)
        else:
            lines = [f"{level_emoji} {payload.title} {cat_emoji}", "", payload.message]
            if payload.metadata:
                lines.append("")
                lines.append("Details:")
                for k, v in list(payload.metadata.items())[:10]:
                    lines.append(f"  {k}: {v}")
            return "\n".join(lines)

    @staticmethod
    def _escape_html(text: str) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")