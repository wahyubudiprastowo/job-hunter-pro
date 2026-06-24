"""
AI Cover Letter Generator (Phase 2c, Patch 10).

For each Easy Apply job that has a cover letter field, generates a tailored
~250-word cover letter referencing:
- Company name
- 1+ specific JD detail (proves AI read JD)
- Real candidate experience from CV
- Localized salutation if non-English

Anti-hallucination guards via cover_letter_validator.py.

Output: cover_letters/generated/{Company}_{JobID}.txt + .pdf
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from loguru import logger

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

# Optional validator (Patch 10)
try:
    from packages.ai.cover_letter_validator import (
        validate_cover_letter,
        log_validation_result,
    )
    _HAS_VALIDATOR = True
except ImportError:
    _HAS_VALIDATOR = False
    validate_cover_letter = None
    log_validation_result = None


# ============================================================
# Language detection (heuristic by common job description words)
# ============================================================

LANG_KEYWORDS = {
    "it": ["sviluppatore", "ingegnere", "esperienza", "competenze", "richiede"],
    "es": ["desarrollador", "ingeniero", "experiencia", "requisitos", "habilidades"],
    "fr": ["développeur", "ingénieur", "expérience", "compétences", "exigences"],
    "de": ["entwickler", "ingenieur", "erfahrung", "kenntnisse", "anforderungen"],
    "nl": ["ontwikkelaar", "ingenieur", "ervaring", "vaardigheden", "vereisten"],
    "pt": ["desenvolvedor", "engenheiro", "experiência", "habilidades", "requisitos"],
}

SALUTATIONS = {
    "en": "Dear Hiring Manager,",
    "it": "Egregio Responsabile delle Assunzioni,",
    "es": "Estimado equipo de selección,",
    "fr": "Madame, Monsieur,",
    "de": "Sehr geehrte Damen und Herren,",
    "nl": "Geachte heer/mevrouw,",
    "pt": "Prezado responsável,",
}

CLOSINGS = {
    "en": "Sincerely,",
    "it": "Cordiali saluti,",
    "es": "Atentamente,",
    "fr": "Cordialement,",
    "de": "Mit freundlichen Grüßen,",
    "nl": "Met vriendelijke groet,",
    "pt": "Atenciosamente,",
}


def _detect_language(job_description: str) -> str:
    """Heuristic language detection by keyword frequency."""
    if not job_description:
        return "en"
    text = job_description.lower()
    scores = {"en": 0}
    for lang, keywords in LANG_KEYWORDS.items():
        scores[lang] = sum(1 for k in keywords if k in text)
    best_lang = max(scores, key=scores.get)
    return best_lang if scores[best_lang] >= 2 else "en"


# ============================================================
# Prompt template (cover.v1 from docs/08)
# ============================================================

COVER_LETTER_PROMPT_TEMPLATE = """You write authentic, concise cover letters.

GOAL: Generate a cover letter for the candidate applying to this job.

STRICT REQUIREMENTS:
- Total length: 200-280 words (1 page)
- Address: "{salutation}" (no name, generic)
- Para 1 (~50 words): Hook — reference ONE specific detail from the JD that excites you
- Para 2 (~100 words): Evidence — 2-3 CONCRETE examples from CV that map to JD requirements
- Para 3 (~50 words): Close — brief enthusiasm + availability mention
- End with "{closing}\n[Candidate Name]"

CRITICAL RULES:
- NEVER claim skills/tools NOT in the candidate's CV
- NEVER inflate years of experience
- NEVER use buzzwords without substance ("passionate", "results-driven", "revolutionary")
- NEVER start with "I am writing to apply for" or similar generic openers
- Reference the company "{company}" by name at least once
- Reference at least one specific JD detail (proves you read the JD)
- Use language: {language_name}

OUTPUT FORMAT:
Plain text only. No markdown, no JSON, no headers other than salutation.

CANDIDATE CV:
{cv_text}

TARGET JOB:
Title: {job_title}
Company: {company}
Description:
{job_description}
"""

LANGUAGE_NAMES = {
    "en": "English", "it": "Italian", "es": "Spanish",
    "fr": "French", "de": "German", "nl": "Dutch", "pt": "Portuguese",
}


# ============================================================
# Helpers
# ============================================================

def _safe_filename(s: str) -> str:
    """Sanitize string for filesystem path."""
    s = re.sub(r"[^\w\s-]", "", s)[:50]
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "cover"


def _safe_format(template: str, **kwargs) -> str:
    """Safe format that handles {} in user content (carry-over from Patch 9)."""
    return template.format(**kwargs)


# ============================================================
# Main generator
# ============================================================

def generate_cover_letter(
    ai,
    profile,
    cv_text: str,
    job,
    output_dir: str = "cover_letters/generated",
    validator_strict: bool = True,
    candidate_facts: Optional[dict] = None,
) -> Optional[tuple]:
    """
    Generate cover letter for a job.

    Returns:
        (txt_path, pdf_path) tuple if success, None on failure.
    """
    if not ai or not ai.is_available():
        logger.debug("AI not available for cover letter generation.")
        return None

    if not cv_text:
        logger.debug("No CV text for cover letter — skipping.")
        return None

    if not job.description:
        logger.debug("No JD — skipping cover letter.")
        return None

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_company = _safe_filename(job.company or "company")
    cache_key = f"{safe_company}_{job.job_id}"
    txt_path = out_dir / f"{cache_key}.txt"
    pdf_path = out_dir / f"{cache_key}.pdf"

    # Cache check
    if txt_path.exists() and pdf_path.exists():
        logger.info(f"💌 Reusing cached cover letter: {txt_path}")
        return (str(txt_path), str(pdf_path))

    # Detect language
    lang = _detect_language(job.description)
    salutation = SALUTATIONS.get(lang, SALUTATIONS["en"])
    closing = CLOSINGS.get(lang, CLOSINGS["en"])
    lang_name = LANGUAGE_NAMES.get(lang, "English")

    # Build prompt
    try:
        sys_prompt = _safe_format(
            COVER_LETTER_PROMPT_TEMPLATE,
            salutation=salutation,
            closing=closing,
            company=job.company or "",
            language_name=lang_name,
            cv_text=cv_text[:4500],
            job_title=job.title or "",
            job_description=(job.description or "")[:2500],
        )
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Cover letter prompt format failed: {e}")
        return None

    raw = ai.chat(
        system=sys_prompt,
        user="Generate the cover letter now. Plain text only.",
        max_tokens=600,
    )
    if not raw:
        logger.warning("AI returned empty for cover letter.")
        return None

    # Strip any markdown or extra wrapping
    text = raw.strip()
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    # Substitute candidate name placeholder if AI used [Candidate Name]
    candidate_name = f"{profile.first_name} {profile.last_name}".strip()
    text = text.replace("[Candidate Name]", candidate_name)
    text = text.replace("[Your Name]", candidate_name)

    # === Validation ===
    if _HAS_VALIDATOR:
        result = validate_cover_letter(
            text=text,
            company=job.company or "",
            job_description=job.description or "",
            cv_text=cv_text,
            candidate_facts=candidate_facts,
            strict=validator_strict,
        )
        log_validation_result(result, job_id=job.job_id)

        if not result.is_valid:
            # Save rejected text for audit
            try:
                audit_path = out_dir / f"{cache_key}.rejected.json"
                audit_path.write_text(
                    json.dumps({
                        "rejected_at": datetime.utcnow().isoformat(),
                        "reasons": result.reasons,
                        "word_count": result.word_count,
                        "new_tech": result.new_tech,
                        "has_company": result.has_company,
                        "has_jd_reference": result.has_jd_reference,
                        "cover_letter_text": text,
                    }, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                logger.debug(f"📋 Cover letter rejection audit: {audit_path}")
            except Exception:
                pass
            return None
    else:
        logger.warning("cover_letter_validator unavailable — anti-hallucination disabled")

    # Save text
    try:
        txt_path.write_text(text, encoding="utf-8")
        logger.success(f"💌 Generated cover letter: {txt_path}")
    except Exception as e:
        logger.error(f"Cover letter txt save failed: {e}")
        return None

    # Render PDF (optional but recommended)
    if _HAS_REPORTLAB:
        try:
            _render_cover_letter_pdf(profile, text, pdf_path, lang)
            return (str(txt_path), str(pdf_path))
        except Exception as e:
            logger.warning(f"Cover letter PDF render failed (txt still available): {e}")
            return (str(txt_path), None)
    else:
        return (str(txt_path), None)


def _render_cover_letter_pdf(profile, text: str, output_path: Path, lang: str = "en"):
    """Render cover letter to PDF using reportlab."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    header = ParagraphStyle(
        "Header", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, textColor="#1a1a1a"
    )
    contact = ParagraphStyle(
        "Contact", parent=styles["Normal"],
        fontSize=9, textColor="#555555", spaceAfter=4
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=8, leading=14, alignment=TA_JUSTIFY
    )

    story = []
    name = f"{profile.first_name} {profile.last_name}".strip()

    # Header with candidate name + contact
    story.append(Paragraph(f"<b>{name}</b>", header))
    contact_parts = [profile.email, profile.phone]
    contact_parts = [p for p in contact_parts if p]
    if contact_parts:
        story.append(Paragraph(" · ".join(contact_parts), contact))
    if profile.linkedin_url:
        story.append(Paragraph(profile.linkedin_url, contact))
    story.append(Spacer(1, 18))

    # Body paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        # Escape special chars for reportlab
        para_safe = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(para_safe, body))

    doc.build(story)
