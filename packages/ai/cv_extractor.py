"""
CV → structured facts extractor (PATCH 7).

Supports:
- PDF text extraction (pypdf)
- DOCX text extraction (python-docx)
- Plain TXT files
- OCR fallback for image-based PDFs (if pytesseract + pdf2image installed)

Auto-detects file format and tries best extractor.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    import PyPDF2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

try:
    from docx import Document
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False


def extract_cv_text(cv_path: str) -> Optional[str]:
    """
    Extract text from CV file. Auto-detect format.

    Tries in order:
    1. If path is .txt → read as text
    2. If path is .docx → use python-docx
    3. If path is .pdf → use pypdf
    4. If PDF returns empty → try sibling .txt file
    5. If PDF returns empty → try OCR (if available)
    """
    path = Path(cv_path)

    # === Try .txt sibling first (manual fallback for image PDFs) ===
    txt_sibling = path.with_suffix(".txt")
    if txt_sibling.exists():
        try:
            text = txt_sibling.read_text(encoding="utf-8")
            if text.strip():
                logger.info(f"📄 Loaded CV from TXT: {txt_sibling}")
                return _clean_text(text)
        except Exception as e:
            logger.debug(f"TXT read failed: {e}")

    # === If file doesn't exist ===
    if not path.exists():
        logger.warning(f"CV file not found: {cv_path}")
        return None

    suffix = path.suffix.lower()

    # === Plain text ===
    if suffix == ".txt":
        try:
            text = path.read_text(encoding="utf-8")
            if text.strip():
                logger.info(f"📄 Loaded CV (TXT, {len(text)} chars)")
                return _clean_text(text)
        except Exception as e:
            logger.error(f"TXT read failed: {e}")

    # === DOCX ===
    if suffix == ".docx" and _HAS_DOCX:
        try:
            doc = Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text.strip():
                logger.info(f"📄 Loaded CV (DOCX, {len(text)} chars)")
                return _clean_text(text)
        except Exception as e:
            logger.error(f"DOCX read failed: {e}")

    # === PDF ===
    if suffix == ".pdf":
        text = _extract_pdf(path)
        if text and len(text.strip()) > 50:
            return _clean_text(text)

        # PDF empty → likely image-based, try OCR
        logger.warning(
            f"⚠️  PDF '{path}' returned empty text (likely image-based PDF). "
            "Trying OCR fallback...")
        ocr_text = _try_ocr(path)
        if ocr_text:
            return _clean_text(ocr_text)

        # OCR also failed — give actionable advice
        logger.error(
            f"❌ Could not extract CV from {path}. The PDF appears to be image-based.\n"
            f"   Solutions:\n"
            f"   1. Re-save the CV from Word/Google Docs as a TEXT-BASED PDF\n"
            f"   2. OR install OCR: pip install pdf2image pytesseract Pillow\n"
            f"      (also need Tesseract OCR binary installed)\n"
            f"   3. OR create resumes/base_resume.txt with plain text content"
        )
    return None


def _extract_pdf(path: Path) -> str:
    """Try pypdf, fall back to PyPDF2."""
    if _HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                logger.info(f"📄 Loaded CV (PDF/pypdf, {len(text)} chars)")
                return text
        except Exception as e:
            logger.debug(f"pypdf failed: {e}")

    if _HAS_PYPDF2:
        try:
            reader = PyPDF2.PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                logger.info(f"📄 Loaded CV (PDF/PyPDF2, {len(text)} chars)")
                return text
        except Exception as e:
            logger.debug(f"PyPDF2 failed: {e}")

    return ""


def _try_ocr(pdf_path: Path) -> Optional[str]:
    """OCR fallback. Returns None if OCR libs not installed."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        logger.debug("OCR libs not installed (pdf2image + pytesseract)")
        return None

    try:
        logger.info("🔍 Running OCR on PDF (this may take 30-60 seconds)...")
        images = convert_from_path(str(pdf_path), dpi=200)
        all_text = []
        for i, img in enumerate(images):
            logger.debug(f"OCR page {i+1}/{len(images)}")
            page_text = pytesseract.image_to_string(img)
            all_text.append(page_text)
        text = "\n\n".join(all_text)
        if text.strip():
            logger.success(f"📄 OCR extracted {len(text)} chars from PDF")
            return text
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        if "tesseract" in str(e).lower():
            logger.error(
                "Tesseract binary not found. Install from: "
                "https://github.com/UB-Mannheim/tesseract/wiki")
    return None


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines)
    if len(cleaned) > 6000:
        cleaned = cleaned[:6000] + "\n[... CV truncated ...]"
    return cleaned


def build_enriched_facts(profile, answer_bank: dict, cv_text: Optional[str]) -> str:
    """Build facts including CV content."""
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

    if cv_text:
        facts.append("\n# === FULL CV CONTENT (authoritative source for tech/skills) ===")
        facts.append(cv_text)
        facts.append("# === END CV ===\n")

    if answer_bank:
        facts.append("\n# Previously answered questions (for consistency)")
        for q, a in list(answer_bank.items())[:25]:
            facts.append(f'- "{q}" -> "{a}"')

    return "\n".join(facts)
