"""Shared data models for all extractors and core engine."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class ApplyStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"
    NEEDS_ANSWERS = "needs_answers"
    PENDING_REVIEW = "pending_review"
    EXTERNAL = "external"


class SkipReason(str, Enum):
    BLACKLISTED_COMPANY = "blacklisted_company"
    BLACKLISTED_TITLE = "blacklisted_title"
    EXCLUDED_KEYWORD = "excluded_keyword"
    SALARY_TOO_LOW = "salary_too_low"
    DUPLICATE = "duplicate"
    NOT_EASY_APPLY = "not_easy_apply"
    DAILY_CAP_REACHED = "daily_cap_reached"
    FIT_SCORE_LOW = "fit_score_low"
    LOCATION_MISMATCH = "location_mismatch"
    UNKNOWN = "unknown"


class SearchFilters(BaseModel):
    queries: list[str] = []
    location: str = ""
    remote: bool = False
    hybrid: bool = False
    date_posted: str = "past_week"
    experience_levels: list[str] = []
    job_type: str = "Full-time"
    easy_apply_only: bool = True


class JobListing(BaseModel):
    platform: str
    job_id: str
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    salary: str = ""
    work_mode: str = ""
    posted_date: Optional[str] = None
    is_easy_apply: bool = False
    raw: dict = Field(default_factory=dict)


class UnansweredQuestion(BaseModel):
    question: str
    field_type: str = "text"  # text | select | radio | checkbox | file
    options: list[str] = []
    job_id: Optional[str] = None
    platform: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApplicationResult(BaseModel):
    status: ApplyStatus
    skip_reason: Optional[SkipReason] = None
    error_message: Optional[str] = None
    unanswered_questions: list[UnansweredQuestion] = Field(default_factory=list)
    qa_log: list[dict] = Field(default_factory=list)
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    fit_score: Optional[int] = None
    fit_reasoning: Optional[str] = None
    applied_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateProfile(BaseModel):
    """All personal info needed to fill applications."""
    first_name: str
    last_name: str
    email: str
    phone: str
    phone_country_code: str = ""
    city: str = ""
    country: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    years_experience: str = ""
    current_company: str = ""
    current_title: str = ""
    highest_education: str = ""
    authorized_to_work: str = "Yes"
    require_sponsorship: str = "No"
    willing_to_relocate: str = "Yes"
    notice_period_days: str = ""
    expected_salary: str = ""
    current_salary: str = ""

    def as_field_map(self) -> dict[str, str]:
        """Return common LinkedIn field-label substrings → value mapping."""
        return {
            "first name": self.first_name,
            "last name": self.last_name,
            "email": self.email,
            "phone country": self.phone_country_code,
            "mobile phone number": self.phone,
            "phone number": self.phone,
            "phone": self.phone,
            "city": self.city,
            "country": self.country,
            "linkedin": self.linkedin_url,
            "github": self.github_url,
            "portfolio": self.portfolio_url,
            "years of experience": self.years_experience,
            "current company": self.current_company,
            "current title": self.current_title,
            "highest level of education": self.highest_education,
            "authorized to work": self.authorized_to_work,
            "require sponsorship": self.require_sponsorship,
            "sponsorship": self.require_sponsorship,
            "willing to relocate": self.willing_to_relocate,
            "notice period": self.notice_period_days,
            "expected salary": self.expected_salary,
            "current salary": self.current_salary,
        }
