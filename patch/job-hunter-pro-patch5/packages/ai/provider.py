"""
OpenAI-compatible chat client.

Works with:
- OpenAI (api.openai.com)
- OmniRouter VS Code Token Alias endpoints (URL-embedded token)
- OpenWebUI / Ollama (custom base_url)

PATCH 5: smarter base_url handling — auto-detects URL-embedded tokens
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
    """Normalize base URL — strip trailing slash, fix common patterns."""
    if not base_url:
        return ""
    url = base_url.strip().rstrip("/")
    return url


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

        # If token is URL-embedded (VS Code alias), api_key can be dummy
        # but openai SDK requires it set, so use placeholder if missing
        if not api_key:
            # Check if URL has embedded token (heuristic: /vscode/sk-... or /key/sk-...)
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
            # Mask key in logs
            masked_key = (api_key[:7] + "..." + api_key[-4:]) if len(api_key) > 12 else "***"
            logger.info(f"🧠 AI provider ready: model={self.model}, base_url={base_url}, key={masked_key}")
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
        """Quick connectivity test. Returns (ok, message)."""
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
                return False, f"404 — check AI_BASE_URL or model name '{self.model}'"
            return False, f"Connection failed: {e}"

    def chat(self, system: str, user: str, max_tokens: int = 256) -> Optional[str]:
        if not self.is_available():
            return None
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
                return resp.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "401" in err_str or "unauthorized" in err_str:
                    if not self._auth_warned:
                        logger.error(
                            "❌ AI 401 Unauthorized. Check AI_API_KEY and AI_BASE_URL in .env. "
                            "AI disabled for this run.")
                        self._auth_warned = True
                    self.enabled = False
                    return None
                attempts += 1
                if attempts <= self.max_retries:
                    logger.warning(f"AI call failed (attempt {attempts}): {e}. Retry in {self.retry_backoff}s")
                    time.sleep(self.retry_backoff)
        self._failure_until = time.time() + self.cooldown
        logger.error(f"AI provider cooldown {self.cooldown}s. Last error: {last_err}")
        return None
