"""
OpenAI-compatible chat client.

Works with any provider that exposes an OpenAI /v1/chat/completions endpoint:
- OpenAI (api.openai.com)
- OmniRouter / OpenWebUI (custom base_url)
- DeepSeek, Mistral, Groq, Together.ai, etc.
- Local Ollama (http://localhost:11434/v1)
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


class AIProvider:
    """Generic OpenAI-compatible chat client with retry + cooldown."""

    def __init__(self, ai_config: dict):
        self.cfg = ai_config
        self.enabled = ai_config.get("enabled", False)
        self.model = ai_config.get("model", "gpt-4o-mini")
        self.temperature = float(ai_config.get("temperature", 0.2))
        self.timeout = int(ai_config.get("timeout_seconds", 60))
        self.max_retries = int(ai_config.get("max_retries", 1))
        self.retry_backoff = int(ai_config.get("retry_backoff_sec", 3))
        self.cooldown = int(ai_config.get("failure_cooldown_seconds", 300))
        self._failure_until = 0  # epoch

        # API key & base_url: env first, then config
        api_key = (os.getenv("AI_API_KEY") or ai_config.get("api_key") or "").strip()
        base_url = (os.getenv("AI_BASE_URL") or ai_config.get("base_url") or "").strip()

        if not self.enabled:
            self.client = None
            return

        if not _HAS_OPENAI:
            logger.error("openai package not installed. pip install openai")
            self.enabled = False
            self.client = None
            return

        if not api_key:
            logger.warning("AI enabled but no API key found. Set AI_API_KEY in .env or ai.api_key in config.yaml")
            self.enabled = False
            self.client = None
            return

        kwargs = {"api_key": api_key, "timeout": self.timeout}
        if base_url:
            kwargs["base_url"] = base_url

        try:
            self.client = OpenAI(**kwargs)
            logger.info(f"🧠 AI provider ready: model={self.model}, base_url={base_url or 'default'}")
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

    def chat(self, system: str, user: str, max_tokens: int = 256) -> Optional[str]:
        """Single chat completion. Returns text or None on failure."""
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
                attempts += 1
                if attempts <= self.max_retries:
                    logger.warning(f"AI call failed (attempt {attempts}): {e}. Retrying in {self.retry_backoff}s...")
                    time.sleep(self.retry_backoff)

        # All retries exhausted — set cooldown
        self._failure_until = time.time() + self.cooldown
        logger.error(f"AI provider failing — cooldown {self.cooldown}s. Last error: {last_err}")
        return None
