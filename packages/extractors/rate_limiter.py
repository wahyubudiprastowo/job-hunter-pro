"""
Smart Rate Limiter (Patch 19).

Cross-run daily-cap and cooldown protection backed by SQLite.
Supports either an existing sqlite3 connection or a database path.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger


RATE_LIMIT_TEXTS = [
    "we limit daily submissions",
    "save this job and apply tomorrow",
    "limit daily applications",
    "apply tomorrow",
    "limit the number of applications",
    "tagliche bewerbungslimit",
    "morgen erneut versuchen",
    "tagliches limit",
    "limite giornaliero",
    "candidati domani",
    "limite di candidature",
    "limite diario",
    "vuelve manana",
    "limite de aplicaciones",
    "limite quotidienne",
    "reessayez demain",
    "limite de candidatures",
    "dagelijkse limiet",
    "morgen opnieuw",
    "limite diario",
    "candidate-se amanha",
    "daglig grans",
]

DEFAULT_DAILY_CAP = 12
DEFAULT_COOLDOWN_HOURS = 24
DEFAULT_REDUCTION_FACTOR = 0.5
DEFAULT_REDUCTION_DAYS = 7


@dataclass
class RateLimitStatus:
    platform: str
    today_date: str
    count_today: int = 0
    cap_today: int = DEFAULT_DAILY_CAP
    blocked_until: Optional[int] = None
    last_warning_at: Optional[int] = None
    cap_reduction_active: bool = False
    cap_reduction_expires_at: Optional[int] = None

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked_until and time.time() < self.blocked_until)

    @property
    def remaining_today(self) -> int:
        return max(0, self.cap_today - self.count_today)

    @property
    def is_at_cap(self) -> bool:
        return self.count_today >= self.cap_today

    @property
    def utilization_pct(self) -> int:
        if self.cap_today <= 0:
            return 100
        return min(100, int((self.count_today / self.cap_today) * 100))

    @property
    def cooldown_remaining_hours(self) -> Optional[float]:
        if not self.is_blocked or not self.blocked_until:
            return None
        return round((self.blocked_until - time.time()) / 3600, 1)

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "today_date": self.today_date,
            "count_today": self.count_today,
            "cap_today": self.cap_today,
            "blocked_until": self.blocked_until,
            "last_warning_at": self.last_warning_at,
            "cap_reduction_active": self.cap_reduction_active,
            "cap_reduction_expires_at": self.cap_reduction_expires_at,
            "is_blocked": self.is_blocked,
            "remaining_today": self.remaining_today,
            "is_at_cap": self.is_at_cap,
            "utilization_pct": self.utilization_pct,
            "cooldown_remaining_hours": self.cooldown_remaining_hours,
        }


def _strip_accents(text: str) -> str:
    translation = str.maketrans({
        "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a", "å": "a",
        "é": "e", "è": "e", "ë": "e", "ê": "e",
        "í": "i", "ì": "i", "ï": "i", "î": "i",
        "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
        "ú": "u", "ù": "u", "ü": "u", "û": "u",
        "ñ": "n", "ç": "c",
    })
    return text.translate(translation)


def detect_rate_limit(html: str) -> bool:
    if not html:
        return False
    text = _strip_accents(str(html).lower())
    return any(phrase in text for phrase in RATE_LIMIT_TEXTS)


def detect_rate_limit_in_driver(driver) -> Optional[str]:
    try:
        html = driver.page_source
    except Exception as e:
        logger.debug(f"Cannot read page source for rate limiter: {e}")
        return None

    if not html:
        return None

    text = _strip_accents(str(html).lower())
    for phrase in RATE_LIMIT_TEXTS:
        if phrase in text:
            return phrase
    return None


def _resolve_db_path(db_source) -> Path:
    if isinstance(db_source, sqlite3.Connection):
        return Path(":memory:")
    if db_source is None:
        return Path("data/applications.db")
    return Path(db_source)


def _connect(db_source):
    if isinstance(db_source, sqlite3.Connection):
        return db_source, False
    path = _resolve_db_path(db_source)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(path)), True


def init_schema(db_source=None):
    conn, should_close = _connect(db_source)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                platform TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                blocked_until INTEGER,
                last_warning_at INTEGER,
                cap_reduction_active INTEGER DEFAULT 0,
                cap_reduction_expires_at INTEGER,
                PRIMARY KEY (platform, date)
            )
            """
        )
        conn.commit()
    finally:
        if should_close:
            conn.close()


class SmartRateLimiter:
    def __init__(self, db_source, platform: str, config: Optional[dict] = None):
        self.db_source = db_source
        self.platform = platform
        config = config or {}
        self.base_cap = int(config.get("total_apply_per_day", DEFAULT_DAILY_CAP))
        self.adaptive_throttle = bool(config.get("adaptive_throttle", True))
        self.cooldown_hours = int(config.get("cooldown_hours_on_limit", DEFAULT_COOLDOWN_HOURS))
        self.reduction_factor = float(config.get("cap_reduction_factor", DEFAULT_REDUCTION_FACTOR))
        self.reduction_days = int(config.get("cap_reduction_days", DEFAULT_REDUCTION_DAYS))
        init_schema(self.db_source)
        self._ensure_today_row()

    @property
    def today_date(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    def _ensure_today_row(self):
        conn, should_close = _connect(self.db_source)
        try:
            cursor = conn.execute(
                "SELECT 1 FROM rate_limits WHERE platform=? AND date=?",
                (self.platform, self.today_date),
            )
            if cursor.fetchone() is not None:
                return

            yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT cap_reduction_active, cap_reduction_expires_at "
                "FROM rate_limits WHERE platform=? AND date=?",
                (self.platform, yesterday),
            ).fetchone()

            reduction_active = 0
            reduction_expires = None
            if row:
                reduction_active = row[0] or 0
                reduction_expires = row[1]
                if reduction_expires and time.time() > reduction_expires:
                    reduction_active = 0
                    reduction_expires = None

            conn.execute(
                "INSERT INTO rate_limits (platform, date, count, cap_reduction_active, cap_reduction_expires_at) "
                "VALUES (?, ?, 0, ?, ?)",
                (self.platform, self.today_date, reduction_active, reduction_expires),
            )
            conn.commit()
        finally:
            if should_close:
                conn.close()

    def get_status(self) -> RateLimitStatus:
        self._ensure_today_row()
        conn, should_close = _connect(self.db_source)
        try:
            row = conn.execute(
                "SELECT count, blocked_until, last_warning_at, cap_reduction_active, cap_reduction_expires_at "
                "FROM rate_limits WHERE platform=? AND date=?",
                (self.platform, self.today_date),
            ).fetchone()
            if not row:
                return RateLimitStatus(platform=self.platform, today_date=self.today_date, cap_today=self.base_cap)

            count_today, blocked_until, last_warning_at, reduction_active, reduction_expires = row
            cap_today = self.base_cap
            if reduction_active and reduction_expires:
                if time.time() < reduction_expires:
                    cap_today = max(1, int(self.base_cap * self.reduction_factor))
                else:
                    conn.execute(
                        "UPDATE rate_limits SET cap_reduction_active=0, cap_reduction_expires_at=NULL "
                        "WHERE platform=? AND date=?",
                        (self.platform, self.today_date),
                    )
                    conn.commit()
                    reduction_active = 0
                    reduction_expires = None

            return RateLimitStatus(
                platform=self.platform,
                today_date=self.today_date,
                count_today=count_today or 0,
                cap_today=cap_today,
                blocked_until=blocked_until,
                last_warning_at=last_warning_at,
                cap_reduction_active=bool(reduction_active),
                cap_reduction_expires_at=reduction_expires,
            )
        finally:
            if should_close:
                conn.close()

    def should_block(self) -> tuple[bool, str]:
        status = self.get_status()
        if status.is_blocked:
            return True, f"In cooldown ({status.cooldown_remaining_hours}h remaining)"
        if status.is_at_cap:
            return True, f"Daily cap reached ({status.count_today}/{status.cap_today})"
        return False, ""

    def increment(self):
        self._ensure_today_row()
        conn, should_close = _connect(self.db_source)
        try:
            conn.execute(
                "UPDATE rate_limits SET count = count + 1 WHERE platform=? AND date=?",
                (self.platform, self.today_date),
            )
            conn.commit()
            status = self.get_status()
            logger.debug(
                f"Rate limiter count: {status.count_today}/{status.cap_today} "
                f"({status.utilization_pct}%) for {self.platform}"
            )
        finally:
            if should_close:
                conn.close()

    def record_warning(self, matched_phrase: str = ""):
        self._ensure_today_row()
        now = int(time.time())
        blocked_until = now + (self.cooldown_hours * 3600)
        reduction_expires = now + (self.reduction_days * 86400)

        conn, should_close = _connect(self.db_source)
        try:
            if self.adaptive_throttle:
                conn.execute(
                    "UPDATE rate_limits SET blocked_until=?, last_warning_at=?, cap_reduction_active=1, "
                    "cap_reduction_expires_at=? WHERE platform=? AND date=?",
                    (blocked_until, now, reduction_expires, self.platform, self.today_date),
                )
            else:
                conn.execute(
                    "UPDATE rate_limits SET blocked_until=?, last_warning_at=? WHERE platform=? AND date=?",
                    (blocked_until, now, self.platform, self.today_date),
                )
            conn.commit()
        finally:
            if should_close:
                conn.close()

        phrase_info = f" (matched: '{matched_phrase}')" if matched_phrase else ""
        logger.warning(
            f"Rate limit detected for {self.platform}{phrase_info} - pausing {self.cooldown_hours}h"
        )

    def reset(self):
        self._ensure_today_row()
        conn, should_close = _connect(self.db_source)
        try:
            conn.execute(
                "UPDATE rate_limits SET blocked_until=NULL, cap_reduction_active=0, cap_reduction_expires_at=NULL "
                "WHERE platform=? AND date=?",
                (self.platform, self.today_date),
            )
            conn.commit()
        finally:
            if should_close:
                conn.close()
        logger.info(f"Rate limiter reset for {self.platform}")


def get_status_for_dashboard(db_source, platform: str, config: Optional[dict] = None) -> dict:
    try:
        limiter = SmartRateLimiter(db_source, platform, config)
        return limiter.get_status().to_dict()
    except Exception as e:
        logger.debug(f"Dashboard rate limit status failed: {e}")
        return {"platform": platform, "error": str(e)}


def format_status_banner(status: RateLimitStatus) -> str:
    if status.is_blocked:
        return f"🚫 BLOCKED - cooldown {status.cooldown_remaining_hours}h remaining"
    if status.is_at_cap:
        return f"🛑 Daily cap reached ({status.count_today}/{status.cap_today})"
    if status.cap_reduction_active:
        return f"⚠️ Adaptive throttle active ({status.count_today}/{status.cap_today})"
    if status.utilization_pct >= 80:
        return f"⚠️ Approaching limit ({status.count_today}/{status.cap_today})"
    return f"✅ OK ({status.count_today}/{status.cap_today})"
