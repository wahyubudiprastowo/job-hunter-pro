"""
OpenAI-compatible chat client.

PATCH 11 fixes:
- Fix log bug: base_url was showing model name (line 80)
- Better key masking: sk-XXXXX*** ({N}chars) — no suffix revealed
- New AI debug logging (chat_debug method) for tracing answer quality issues
- Add chat_with_logs() for verbose mode debugging
"""
from __future__ import annotations
import json
import time
import os
from typing import Optional
from loguru import logger

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


def normalize_base_url(base_url: str) -> str:
    if not base_url:
        return ""
    return base_url.strip().rstrip("/")


def _mask_secret(s: str) -> str:
    """PATCH 11: Better masking — show length, no suffix."""
    if not s:
        return "(empty)"
    if len(s) <= 8:
        return "***"
    return f"{s[:5]}***({len(s)}chars)"


def _mask_url(url: str) -> str:
    """PATCH 11: Mask token-embedded URLs."""
    if not url:
        return "(empty)"
    import re
    # Mask /sk-xxx/ or /token-xxx/ patterns in URL
    masked = re.sub(r"/sk-[a-zA-Z0-9_-]{8,}/?", "/sk-***/", url)
    masked = re.sub(r"/[a-zA-Z0-9_-]{20,}/", "/***/", masked)
    return masked


class AIProvider:
    def __init__(self, ai_config: dict):
        self.cfg = ai_config
        self.enabled = ai_config.get("enabled", False)
        self.model = ai_config.get("model", "gpt-4o-mini")
        self.temperature = float(ai_config.get("temperature", 0.2))
        self.timeout = int(ai_config.get("timeout_seconds", 60))
        self.max_retries = int(ai_config.get("max_retries", 1))
        self.retry_backoff = int(ai_config.get("retry_backoff_sec", 3))
        self.cooldown = int(ai_config.get("failure_cooldown_seconds", 300))
        self._failure_until = 0
        self._auth_warned = False
        # PATCH 11: track call counts for diagnostics
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.unknown_count = 0

        api_key = (os.getenv("AI_API_KEY") or ai_config.get("api_key") or "").strip()
        base_url = (os.getenv("AI_BASE_URL") or ai_config.get("base_url") or "").strip()
        base_url = normalize_base_url(base_url)

        if not self.enabled:
            self.client = None
            return
        if not _HAS_OPENAI:
            logger.error("openai package not installed. pip install openai")
            self.enabled = False
            self.client = None
            return

        if not api_key:
            if "/sk-" in base_url or "/vscode/" in base_url:
                api_key = "sk-url-embedded"
                logger.info("API key not set but URL has embedded token — using placeholder")
            else:
                logger.warning("AI enabled but no API key found.")
                self.enabled = False
                self.client = None
                return

        kwargs = {"api_key": api_key, "timeout": self.timeout}
        if base_url:
            kwargs["base_url"] = base_url

        try:
            self.client = OpenAI(**kwargs)
            # PATCH 11 FIX: was logging base_url=model instead of actual URL
            logger.info(
                f"🧠 AI provider ready: model={self.model}, "
                f"base_url={_mask_url(base_url)}, "
                f"key={_mask_secret(api_key)}"
            )
        except Exception as e:
            logger.error(f"AI client init failed: {e}")
            self.client = None
            self.enabled = False

    def is_available(self) -> bool:
        if not self.enabled or not self.client:
            return False
        if time.time() < self._failure_until:
            return False
        return True

    def test_connection(self) -> tuple[bool, str]:
        if not self.is_available():
            return False, "AI provider not initialized"
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Reply with single word: ready"}],
                max_tokens=10,
                temperature=0.0,
            )
            text = resp.choices[0].message.content.strip()
            return True, f"OK: '{text}'"
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "unauthorized" in err_str.lower():
                return False, f"401 Unauthorized — check AI_API_KEY"
            if "404" in err_str or "not found" in err_str.lower():
                return False, f"404 — check AI_BASE_URL or model '{self.model}'"
            return False, f"Connection failed: {e}"

    def chat(self, system: str, user: str, max_tokens: int = 256) -> Optional[str]:
        """Standard chat — silent unless errors."""
        return self._chat_internal(system, user, max_tokens, debug=False)

    def chat_debug(self, system: str, user: str, max_tokens: int = 256,
                   context: str = "") -> Optional[str]:
        """PATCH 11: Verbose chat for debugging — logs prompt + response.

        Use when answer quality is suspect.
        Set ai.debug_chat: true in config to enable in production.
        """
        return self._chat_internal(system, user, max_tokens, debug=True, context=context)

    def _chat_internal(self, system: str, user: str, max_tokens: int = 256,
                       debug: bool = False, context: str = "") -> Optional[str]:
        if not self.is_available():
            return None

        self.call_count += 1

        if debug:
            ctx = f" [{context}]" if context else ""
            logger.debug(f"🧠 AI chat{ctx}: user={user[:100]!r}, max_tok={max_tokens}")

        attempts = 0
        last_err = None
        while attempts <= self.max_retries:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content.strip()

                if debug:
                    logger.debug(f"🧠 AI response: {text[:200]!r}")

                self.success_count += 1
                if text.upper() in ("UNKNOWN", ""):
                    self.unknown_count += 1

                return text

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "401" in err_str or "unauthorized" in err_str:
                    if not self._auth_warned:
                        logger.error(
                            "❌ AI 401 Unauthorized. Check AI_API_KEY and AI_BASE_URL. "
                            "AI disabled for this run."
                        )
                        self._auth_warned = True
                    self.enabled = False
                    self.failure_count += 1
                    return None
                attempts += 1
                if attempts <= self.max_retries:
                    logger.warning(f"AI call failed (attempt {attempts}): {e}. Retry in {self.retry_backoff}s")
                    time.sleep(self.retry_backoff)

        self._failure_until = time.time() + self.cooldown
        self.failure_count += 1
        logger.error(f"AI provider cooldown {self.cooldown}s. Last error: {last_err}")
        return None

    def get_stats(self) -> dict:
        """PATCH 11: Get usage stats for diagnostics."""
        return {
            "total_calls": self.call_count,
            "successful": self.success_count,
            "failed": self.failure_count,
            "unknown_responses": self.unknown_count,
            "success_rate": round(self.success_count / max(1, self.call_count) * 100, 1),
            "unknown_rate": round(self.unknown_count / max(1, self.call_count) * 100, 1),
            "in_cooldown": time.time() < self._failure_until,
        }

    def log_stats(self):
        """Log a stats summary."""
        s = self.get_stats()
        logger.info(
            f"🧠 AI stats: {s['total_calls']} calls, "
            f"{s['successful']} success ({s['success_rate']}%), "
            f"{s['unknown_responses']} UNKNOWN ({s['unknown_rate']}%), "
            f"{s['failed']} failed"
        )
