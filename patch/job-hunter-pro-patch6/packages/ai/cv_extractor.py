"""
CV PDF → structured facts extractor.

Reads the candidate's base resume PDF and extracts:
- Raw text (full CV content)
- Technologies/tools with years of experience (heuristic + AI-assisted)

The extracted CV text becomes part of the system prompt for AI question answering,
so the AI answers based on REAL CV content, not config.yaml guesses.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    import PyPDF2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False


def extract_cv_text(pdf_path: str) -> Optional[str]:
    """Extract plain text from a PDF resume. Returns None on failure."""
    path = Path(pdf_path)
    if not path.exists():
        logger.warning(f"CV file not found: {pdf_path}")
        return None

    # Try pypdf first (newer/recommended)
    if _HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                logger.info(f"📄 Extracted CV ({len(text)} chars) using pypdf")
                return _clean_text(text)
        except Exception as e:
            logger.debug(f"pypdf failed: {e}")

    # Fallback to PyPDF2
    if _HAS_PYPDF2:
        try:
            reader = PyPDF2.PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                logger.info(f"📄 Extracted CV ({len(text)} chars) using PyPDF2")
                return _clean_text(text)
        except Exception as e:
            logger.error(f"PyPDF2 failed: {e}")

    if not _HAS_PYPDF and not _HAS_PYPDF2:
        logger.error("No PDF library installed. Run: pip install pypdf")
        return None

    return None


def _clean_text(text: str) -> str:
    """Clean common PDF extraction noise."""
    # Remove excessive whitespace
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    cleaned = "\n".join(lines)
    # Truncate to ~6000 chars to keep AI prompt manageable
    if len(cleaned) > 6000:
        cleaned = cleaned[:6000] + "\n[... CV truncated ...]"
    return cleaned


def build_enriched_facts(profile, answer_bank: dict, cv_text: Optional[str]) -> str:
    """
    Build candidate facts including CV content.

    The AI will use this as ground truth to answer questions accurately
    (e.g., "Years of Kubernetes experience" → AI reads CV, finds actual mention).
    """
    p = profile
    facts = [
        "# Candidate Profile (from config)",
        f"- Name: {p.first_name} {p.last_name}",
        f"- Email: {p.email}",
        f"- Phone: {p.phone_country_code} {p.phone}",
        f"- Location: {p.city}, {p.country}",
        f"- Current company: {p.current_company}",
        f"- Current title: {p.current_title}",
        f"- Total years of experience: {p.years_experience}",
        f"- Highest education: {p.highest_education}",
        f"- Authorized to work: {p.authorized_to_work}",
        f"- Requires sponsorship: {p.require_sponsorship}",
        f"- Willing to relocate: {p.willing_to_relocate}",
        f"- Notice period (days): {p.notice_period_days}",
        f"- Expected salary: {p.expected_salary}",
        f"- Current salary: {p.current_salary}",
    ]
    if p.linkedin_url:
        facts.append(f"- LinkedIn: {p.linkedin_url}")

    # Append CV content as the authoritative source
    if cv_text:
        facts.append("\n# === FULL CV CONTENT (authoritative source for tech/skills) ===")
        facts.append(cv_text)
        facts.append("# === END CV ===\n")

    # Append previously answered Q/A pairs (helps consistency)
    if answer_bank:
        facts.append("\n# Previously answered questions (for consistency)")
        for q, a in list(answer_bank.items())[:25]:
            facts.append(f'- "{q}" -> "{a}"')

    return "\n".join(facts)
