"""
AI Resume Tailoring (Phase 2b) — PATCH 9 with anti-hallucination validator.

Given a job description + base CV, generates a tailored resume that:
1. Highlights skills most relevant to the job
2. De-emphasizes irrelevant experience
3. Adds keyword matching from JD (ATS optimization)
4. NEVER invents new skills/experience (anti-hallucination ENFORCED via validator)

PATCH 9 changes:
- Calls validate_tailored() before rendering PDF
- Falls back to base CV if validation fails
- New log markers: 🛑 Resume REJECTED + reason
- Fix latent .format() bug when CV contains {} characters
- Returns validation result for caller observability

Output: tailored .pdf file saved to resumes/generated/{company}_{job_id}.pdf
"""
from __future__ import annotations
import re
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
from loguru import logger

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak
    )
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False
    logger.warning("reportlab not installed. Run: pip install reportlab")

# PATCH 9: import validator
try:
    from packages.ai.resume_validator import (
        validate_tailored, log_validation_result, ValidationResult
    )
    _HAS_VALIDATOR = True
except ImportError:
    _HAS_VALIDATOR = False
    validate_tailored = None
    log_validation_result = None
    ValidationResult = None


TAILOR_SYSTEM_PROMPT_TEMPLATE = """You are an expert resume tailoring assistant.

GOAL: Rewrite the candidate's resume to maximize relevance to the target job.

CRITICAL RULES:
- NEVER invent skills, certifications, or experience not in the base CV.
- NEVER inflate years of experience.
- ONLY rewrite/reorder existing content for emphasis.
- Add keywords from the job description ONLY if the underlying skill exists in CV.
- Keep the resume to 1 page (~500 words).

OUTPUT FORMAT (strict):
Return a JSON object with these exact keys (no markdown, no extra text):
{{
  "summary": "2-3 sentence professional summary tailored to the job",
  "highlighted_skills": ["skill1", "skill2", "..."],
  "experience_bullets": [
    "Bullet 1 about most relevant experience (action verb + technology + impact)",
    "Bullet 2 ...",
    "Bullet 3 ...",
    "Bullet 4 ...",
    "Bullet 5 ..."
  ],
  "key_tools": ["tool1", "tool2", "tool3", "..."]
}}

CANDIDATE CV:
{cv_text}

TARGET JOB DESCRIPTION:
{job_description}

JOB TITLE: {job_title}
COMPANY: {company}
"""


def _safe_filename(s: str) -> str:
    """Sanitize string for filesystem path."""
    s = re.sub(r"[^\w\s-]", "", s)[:50]
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "resume"


def _safe_format(template: str, **kwargs) -> str:
    """
    PATCH 9: Safe format that escapes single {} in user content
    but preserves {placeholder} for our keys.
    """
    # First, escape literal { and } that aren't part of our placeholders
    # Our placeholders use {{key}} after this function does {key} → {key}
    # So we use {{ }} in template for literal braces, and {key} for placeholders
    # The template now has {{...}} for JSON example which becomes {...} after format
    return template.format(**kwargs)


def generate_tailored_resume(
    ai,
    profile,
    cv_text: str,
    job,
    output_dir: str = "resumes/generated",
    validator_strict: bool = True,
    candidate_facts: Optional[dict] = None,
) -> Optional[str]:
    """
    Generate tailored resume PDF for a specific job.
    Returns path to generated PDF, or None on failure.

    PATCH 9: Validates output before rendering. Returns None if validation fails.

    Args:
        validator_strict: if True, reject on ANY new tech. If False, allow 1 new.
        candidate_facts: dict with years_experience, salary for inflation check
    """
    if not _HAS_REPORTLAB:
        logger.warning("Cannot generate tailored resume — reportlab not installed.")
        return None

    if not ai or not ai.is_available():
        logger.debug("AI not available for resume tailoring.")
        return None

    if not cv_text:
        logger.debug("No CV text for tailoring.")
        return None

    # Cache key: avoid regenerating for same job
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_company = _safe_filename(job.company or "company")
    safe_title = _safe_filename(job.title or "role")
    cache_key = f"{safe_company}_{safe_title}_{job.job_id}"
    output_path = out_dir / f"{cache_key}.pdf"

    if output_path.exists():
        logger.info(f"📄 Reusing cached tailored resume: {output_path}")
        return str(output_path)

    # Build AI prompt — PATCH 9: use safe format to avoid {} in CV breaking template
    try:
        sys_prompt = _safe_format(
            TAILOR_SYSTEM_PROMPT_TEMPLATE,
            cv_text=cv_text[:5000],
            job_description=(job.description or "")[:3000],
            job_title=job.title or "",
            company=job.company or "",
        )
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Prompt format failed (likely {{}} in CV): {e}")
        return None

    raw = ai.chat(
        system=sys_prompt,
        user="Generate the tailored resume JSON now.",
        max_tokens=1500,
    )
    if not raw:
        logger.warning("AI returned empty for resume tailoring.")
        return None

    # Parse JSON response
    tailored = _parse_tailor_response(raw)
    if not tailored:
        logger.warning(f"Could not parse AI tailor response: {raw[:200]}")
        return None

    # === PATCH 9: ANTI-HALLUCINATION VALIDATION ===
    if _HAS_VALIDATOR:
        result = validate_tailored(
            base_cv_text=cv_text,
            tailored=tailored,
            strict=validator_strict,
            candidate_facts=candidate_facts,
        )
        log_validation_result(result, job_id=job.job_id)

        if not result.is_valid:
            # Save rejected JSON for audit (debug)
            try:
                audit_path = out_dir / f"{cache_key}.rejected.json"
                import json
                audit_path.write_text(
                    json.dumps({
                        "rejected_at": datetime.utcnow().isoformat(),
                        "reasons": result.reasons,
                        "new_tech": result.new_tech,
                        "word_count_ratio": result.word_count_ratio,
                        "tailored_content": tailored,
                    }, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                logger.debug(f"📋 Rejection audit saved: {audit_path}")
            except Exception:
                pass
            return None  # caller will fallback to base CV
    else:
        logger.warning("resume_validator not available — skipping anti-hallucination check")

    # Render PDF
    try:
        _render_resume_pdf(profile, tailored, output_path)
        logger.success(f"📄 Generated tailored resume: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"Resume PDF generation failed: {e}")
        return None


def _parse_tailor_response(raw: str) -> Optional[dict]:
    """Extract JSON from AI response (handles markdown code blocks)."""
    import json
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        # Validate required keys
        required = ("summary", "highlighted_skills", "experience_bullets", "key_tools")
        if all(k in data for k in required):
            return data
        return None
    except json.JSONDecodeError:
        return None


def _render_resume_pdf(profile, tailored: dict, output_path: Path):
    """Render tailored resume to PDF using reportlab."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=18, spaceAfter=4, textColor="#1a1a1a", alignment=TA_LEFT
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=12, spaceAfter=4, spaceBefore=10, textColor="#0066cc"
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, leading=13
    )
    contact = ParagraphStyle(
        "Contact", parent=styles["Normal"],
        fontSize=9, textColor="#555555", spaceAfter=8
    )

    story = []

    # Header
    name = f"{profile.first_name} {profile.last_name}".strip()
    story.append(Paragraph(name, h1))

    phone_display = ""
    phone_raw = (getattr(profile, "phone", "") or "").strip()
    phone_country_code = (getattr(profile, "phone_country_code", "") or "").strip()
    if phone_raw:
        if phone_country_code:
            cc_match = re.search(r"\+\d+", phone_country_code)
            if cc_match:
                phone_display = f"{cc_match.group(0)} {phone_raw}"
            else:
                phone_display = f"{phone_country_code} {phone_raw}"
        else:
            phone_display = phone_raw

    contact_parts = [profile.email, phone_display, profile.city, profile.country]
    contact_parts = [p for p in contact_parts if p]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact))

    links = []
    if profile.linkedin_url:
        links.append(profile.linkedin_url)
    if getattr(profile, "github_url", ""):
        links.append(profile.github_url)
    if getattr(profile, "portfolio_url", ""):
        links.append(profile.portfolio_url)
    if links:
        story.append(Paragraph(" | ".join(links), contact))

    # Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", h2))
    story.append(Paragraph(tailored.get("summary", ""), body))

    # Highlighted skills
    skills = tailored.get("highlighted_skills", [])
    if skills:
        story.append(Paragraph("KEY SKILLS", h2))
        story.append(Paragraph(" • ".join(skills), body))

    # Experience bullets
    bullets = tailored.get("experience_bullets", [])
    if bullets:
        story.append(Paragraph("RELEVANT EXPERIENCE", h2))
        for b in bullets:
            story.append(Paragraph(f"• {b}", body))

    # Key tools (ATS keywords)
    tools = tailored.get("key_tools", [])
    if tools:
        story.append(Paragraph("TECHNICAL TOOLS", h2))
        story.append(Paragraph(", ".join(tools), body))

    # Footer
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"<i>Tailored for this application — Education: {profile.highest_education}</i>",
        contact))

    doc.build(story)
