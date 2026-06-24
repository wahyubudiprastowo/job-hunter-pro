from __future__ import annotations

import os
import time
from typing import Optional

from loguru import logger

from packages.notifications.base import NotificationChannel, NotificationPayload, SendResult


LEVEL_PREFIX = {
    "info": "[INFO]",
    "success": "[OK]",
    "warning": "[WARN]",
    "error": "[ERROR]",
    "critical": "[CRITICAL]",
}


class TelegramChannel(NotificationChannel):
    name = "telegram"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.token = (os.getenv("TELEGRAM_BOT_TOKEN") or self.config.get("token") or "").strip()
        self.chat_id = (os.getenv("TELEGRAM_CHAT_ID") or self.config.get("chat_id") or "").strip()
        self.parse_mode = self.config.get("parse_mode", "HTML")
        self.disable_notification = bool(self.config.get("disable_notification", False))
        self.timeout = int(self.config.get("timeout", 15))
        if self.enabled and (not self.token or not self.chat_id):
            logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
            self.enabled = False

    def send(self, payload: NotificationPayload) -> SendResult:
        if not self.enabled:
            return SendResult(success=False, channel=self.name, error="Channel disabled")

        import requests

        start = time.time()
        text = self._format_message(payload)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": self.parse_mode,
                    "disable_notification": self.disable_notification,
                    "disable_web_page_preview": True,
                },
                timeout=self.timeout,
            )
            data = response.json()
            duration_ms = int((time.time() - start) * 1000)
            if data.get("ok"):
                return SendResult(
                    success=True,
                    channel=self.name,
                    duration_ms=duration_ms,
                    response_data=data.get("result"),
                )
            return SendResult(
                success=False,
                channel=self.name,
                duration_ms=duration_ms,
                error=data.get("description", "Unknown Telegram API error"),
            )
        except Exception as exc:
            return SendResult(success=False, channel=self.name, error=f"Send failed: {exc}")

    def _format_message(self, payload: NotificationPayload) -> str:
        prefix = LEVEL_PREFIX.get(payload.level.value, "[INFO]")
        lines = [f"{prefix} <b>{self._escape_html(payload.title)}</b>", "", self._escape_html(payload.message)]
        if payload.metadata:
            lines.extend(["", "<i>Details:</i>"])
            for key, value in list(payload.metadata.items())[:10]:
                lines.append(f"<code>{self._escape_html(str(key))}</code>: {self._escape_html(str(value))}")
        if payload.timestamp:
            lines.extend(["", f"<i>{payload.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</i>"])
        return "\n".join(lines)

    @staticmethod
    def _escape_html(text: str) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
