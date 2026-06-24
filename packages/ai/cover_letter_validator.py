"""
Cover Letter Anti-Hallucination Validator (PATCH 10).

Implements anti-hallucination guards from docs/20:
- Word count check (250-300 words target)
- Required company name reference
- Required JD-specific detail (proves AI read JD)
- Forbidden phrases (generic openers, fake credentials)
- Tech mentioned must exist in CV (cross-reference)
- Salutation must be appropriate (not "Dear Sir/Madam" if recruiter name known)

Reuses VARIANT_TO_CANONICAL from resume_validator for consistent tech detection.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger

# Reuse tech detection from resume_validator
try:
    from packages.ai.resume_validator import (
        _extract_tech_terms,
        _canonicalize_terms,
        VARIANT_TO_CANONICAL,
        ALL_TECH_TERMS,
    )
    _HAS_RESUME_VALIDATOR = True
except ImportError:
    _HAS_RESUME_VALIDATOR = False
    logger.warning("resume_validator not available — tech cross-reference disabled")


# ============================================================
# Configuration
# ============================================================

MIN_WORDS = 150       # too short = generic
MAX_WORDS = 350       # too long = unprofessional
TARGET_WORDS = 250    # ideal range center

# Forbidden generic openers (per docs/08 cover.v1)
FORBIDDEN_OPENERS = [
    "i am writing to apply for",
    "i am writing to express my interest",
    "please accept this letter as",
    "with great enthusiasm",
    "i would like to apply",
    "this letter serves as",
]

# Forbidden generic phrases (unsubstantiated claims)
FORBIDDEN_PHRASES = [
    ("results-driven", "vague buzzword without substance"),
    ("passionate about", "overused — needs specific detail"),
    ("world-class", "unsubstantiated superlative"),
    ("revolutionary", "marketing fluff"),
    ("synergize", "corporate jargon"),
    ("paradigm shift", "buzzword"),
    ("doctorate", "fake credential indicator"),
    ("phd in", "fake credential indicator"),
    ("nobel prize", "obvious fake"),
    ("ceo of", "title escalation"),
    ("inventor of", "false attribution"),
]

# Multi-language salutations (acceptable)
ACCEPTABLE_SALUTATIONS = [
    # English
    "dear hiring manager", "dear hiring team", "dear recruiter",
    "dear recruiting team", "to the hiring manager",
    # Italian
    "egregio responsabile", "gentile responsabile delle assunzioni",
    # Spanish
    "estimado responsable", "estimado equipo",
    # French
    "madame, monsieur", "monsieur, madame",
    # German
    "sehr geehrte damen und herren", "sehr geehrtes team",
    # Dutch
    "geachte heer/mevrouw", "geacht team",
    # Portuguese
    "prezado responsável", "caros recrutadores",
]


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class CoverLetterValidationResult:
    is_valid: bool
    reasons: list = field(default_factory=list)
    word_count: int = 0
    new_tech: list = field(default_factory=list)
    has_company: bool = False
    has_jd_reference: bool = False
    has_salutation: bool = False
    sanitized: Optional[str] = None

    def reject_reason_summary(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "OK"


# ============================================================
# Main validator
# ============================================================

def validate_cover_letter(
    text: str,
    company: str,
    job_description: str,
    cv_text: Optional[str] = None,
    candidate_facts: Optional[dict] = None,
    min_words: int = MIN_WORDS,
    max_words: int = MAX_WORDS,
    strict: bool = True,
) -> CoverLetterValidationResult:
    """
    Validate cover letter against anti-hallucination rules.

    Args:
        text: cover letter content (plain text)
        company: target company name
        job_description: JD text to verify reference
        cv_text: candidate's base CV for tech cross-check
        candidate_facts: dict with years_experience etc
        strict: if True, fail on ANY new tech / forbidden phrase

    Returns CoverLetterValidationResult.
    """
    result = CoverLetterValidationResult(is_valid=True)
    text_lower = text.lower().strip()

    if not text or len(text_lower) < 50:
        result.is_valid = False
        result.reasons.append("Cover letter too short (<50 chars)")
        return result

    # === Check 1: Word count ===
    words = len(text.split())
    result.word_count = words

    if words < min_words:
        result.is_valid = False
        result.reasons.append(f"Too short: {words} words < {min_words} min")

    if words > max_words:
        result.is_valid = False
        result.reasons.append(f"Too long: {words} words > {max_words} max")

    # === Check 2: Company name reference ===
    if company:
        company_clean = company.strip().lower()
        # Allow company variants (e.g. "Microsoft" matches "Microsoft Corporation")
        company_first_word = company_clean.split()[0] if company_clean else ""
        if company_first_word and company_first_word in text_lower:
            result.has_company = True
        elif company_clean in text_lower:
            result.has_company = True
        else:
            result.is_valid = False
            result.reasons.append(f"Missing company reference: '{company}'")

    # === Check 3: JD-specific detail (proves AI read JD) ===
    if job_description and len(job_description) > 100:
        jd_lower = job_description.lower()
        # Extract significant nouns from JD (length > 5, not common)
        jd_words = set(re.findall(r"\b[a-z][a-z\-]{5,}\b", jd_lower))
        text_words = set(re.findall(r"\b[a-z][a-z\-]{5,}\b", text_lower))

        common_words = {
            "experience", "engineer", "developer", "manager", "company",
            "position", "candidate", "opportunity", "company", "professional",
            "working", "develop", "implement", "create", "design", "support",
            "looking", "skilled", "qualified", "responsible", "various",
            "different", "include", "during", "across", "between", "without",
            "applications", "applicants", "requirements", "available",
        }
        meaningful_jd = jd_words - common_words
        overlap = meaningful_jd & text_words

        if len(overlap) >= 2:
            result.has_jd_reference = True
        elif len(overlap) == 1:
            result.has_jd_reference = True  # 1 is acceptable
        else:
            result.is_valid = False
            result.reasons.append(
                "No JD-specific reference — AI may not have read JD"
            )

    # === Check 4: Acceptable salutation ===
    first_100 = text_lower[:100]
    for salutation in ACCEPTABLE_SALUTATIONS:
        if salutation in first_100:
            result.has_salutation = True
            break

    if not result.has_salutation:
        # Soft check — only fail if also has generic opener
        for opener in FORBIDDEN_OPENERS:
            if opener in first_100:
                result.is_valid = False
                result.reasons.append(f"Generic opener: '{opener}'")
                break

    # === Check 5: Forbidden phrases ===
    forbidden_hits = []
    for pattern, why in FORBIDDEN_PHRASES:
        if pattern in text_lower:
            forbidden_hits.append(f"'{pattern}' ({why})")

    if forbidden_hits:
        if strict:
            result.is_valid = False
            result.reasons.append(f"Forbidden phrases: {forbidden_hits[:3]}")
        elif len(forbidden_hits) > 2:
            result.is_valid = False
            result.reasons.append(f"Multiple forbidden phrases: {forbidden_hits[:3]}")

    # === Check 6: Tech cross-reference with CV ===
    if cv_text and _HAS_RESUME_VALIDATOR:
        cv_tech_raw = _extract_tech_terms(cv_text)
        letter_tech_raw = _extract_tech_terms(text)
        cv_tech = _canonicalize_terms(cv_tech_raw)
        letter_tech = _canonicalize_terms(letter_tech_raw)
        new_tech = sorted(letter_tech - cv_tech)

        if new_tech:
            result.new_tech = new_tech
            if strict:
                result.is_valid = False
                result.reasons.append(
                    f"AI invented {len(new_tech)} tech not in CV: "
                    f"{', '.join(new_tech[:5])}"
                )
            elif len(new_tech) > 1:
                result.is_valid = False
                result.reasons.append(
                    f"AI invented {len(new_tech)} tech (soft limit=1): "
                    f"{', '.join(new_tech)}"
                )

    # === Check 7: Years/numerics inflation (if candidate_facts) ===
    if candidate_facts:
        try:
            actual_years = int(candidate_facts.get("years_experience", 0))
        except (ValueError, TypeError):
            actual_years = 0

        years_pattern = r"(\d+)[\s+\-]*(?:year|yr)s?"
        for m in re.findall(years_pattern, text_lower):
            try:
                claimed = int(m)
                if actual_years > 0 and claimed > actual_years * 1.5:
                    result.is_valid = False
                    result.reasons.append(
                        f"Years inflation: claimed {claimed} but candidate has {actual_years}"
                    )
                    break
            except ValueError:
                continue

    # If valid: provide sanitized version
    if result.is_valid:
        result.sanitized = text.strip()

    return result


def log_validation_result(result: CoverLetterValidationResult, job_id: str = ""):
    """Log validation result with appropriate emoji + level."""
    suffix = f" [job={job_id}]" if job_id else ""
    if result.is_valid:
        logger.success(
            f"💌 Cover letter validated{suffix}: "
            f"{result.word_count} words, "
            f"company={'✓' if result.has_company else '✗'}, "
            f"jd_ref={'✓' if result.has_jd_reference else '✗'}"
        )
    else:
        logger.warning(
            f"🛑 Cover letter REJECTED{suffix}: {result.reject_reason_summary()}"
        )
        if result.new_tech:
            logger.debug(f"   Invented tech: {result.new_tech}")
