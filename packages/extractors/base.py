"""
Base interface for all job-platform extractors.

Every platform plugin (LinkedIn, Indeed, Glassdoor, JobStreet, etc.)
MUST implement this interface. The orchestrator only ever calls these
methods — it has no platform-specific knowledge.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator
from packages.core.models import (
    SearchFilters, JobListing, ApplicationResult, CandidateProfile
)


class BaseExtractor(ABC):
    """Abstract base class for a job platform integration."""

    #: Short identifier ("linkedin", "indeed", etc.)
    name: str = "base"

    #: Public base URL of the platform.
    base_url: str = ""

    #: True if login required before search/apply.
    requires_login: bool = True

    #: True if this extractor supports a 1-click style apply.
    supports_easy_apply: bool = True

    def __init__(self, driver, config: dict, profile: CandidateProfile,
                 answer_bank: dict, stealth_cfg: dict):
        self.driver = driver
        self.config = config
        self.profile = profile
        self.answer_bank = answer_bank
        self.stealth_cfg = stealth_cfg

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @abstractmethod
    def login(self, email: str, password: str, totp_secret: str = "") -> bool:
        """Authenticate. Return True on success."""

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    @abstractmethod
    def search(self, filters: SearchFilters) -> None:
        """Navigate to the search results page for one query."""

    @abstractmethod
    def collect_job_cards(self, max_cards: int = 50) -> list[dict]:
        """Return a list of lightweight job-card dicts on the current page."""

    @abstractmethod
    def open_job_detail(self, card: dict) -> JobListing:
        """Click into a job card and return the full JobListing."""

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    @abstractmethod
    def can_auto_apply(self, job: JobListing) -> bool:
        """Quick check whether the bot can attempt to apply."""

    @abstractmethod
    def apply(self, job: JobListing, resume_path: str,
              mode: str = "semi_auto", cover_letter_paths: dict | None = None) -> ApplicationResult:
        """Run the full apply flow and return the result."""

    # ------------------------------------------------------------------
    # Optional hooks (override if supported)
    # ------------------------------------------------------------------
    def get_application_status(self, job_id: str) -> str:
        """Return current ATS status for a previously-applied job."""
        return "unknown"

    def close(self):
        """Optional cleanup hook."""
        return None
