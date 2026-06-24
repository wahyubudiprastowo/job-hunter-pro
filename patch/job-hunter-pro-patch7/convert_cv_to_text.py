"""
Helper script: diagnose and fix CV PDF text extraction.

Usage from project root:
    python convert_cv_to_text.py
"""
import sys
from pathlib import Path

CV_PATH = Path("resumes/base_resume.pdf")
TXT_PATH = Path("resumes/base_resume.txt")


def main():
    if not CV_PATH.exists():
        print(f"[ERROR] {CV_PATH} not found.")
        return

    print(f"[INFO] Found CV: {CV_PATH} ({CV_PATH.stat().st_size // 1024} KB)")

    # Try pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(str(CV_PATH))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        print(f"[INFO] pypdf extracted {len(text)} chars from {len(reader.pages)} pages")
        if len(text.strip()) > 100:
            print("[SUCCESS] CV is text-based! No fix needed.")
            print(f"\nFirst 500 chars:\n{text[:500]}")
            return
    except Exception as e:
        print(f"[WARN] pypdf failed: {e}")

    print("\n[WARN] PDF appears to be IMAGE-BASED (scan or image export).")
    print("[INFO] Trying OCR fallback...\n")

    # Try OCR
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        print("[INFO] OCR libs not installed. Install with:")
        print("       pip install pdf2image pytesseract Pillow")
        print("\n[INFO] Plus install Tesseract binary:")
        print("       https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n[INFO] OR easier: create resumes/base_resume.txt manually")
        print("       with the plain text content of your CV.")
        return

    try:
        print("[INFO] Converting PDF pages to images...")
        images = convert_from_path(str(CV_PATH), dpi=200)
        print(f"[INFO] OCR'ing {len(images)} pages...")
        texts = []
        for i, img in enumerate(images):
            print(f"  Page {i+1}/{len(images)}...")
            texts.append(pytesseract.image_to_string(img))
        text = "\n\n".join(texts)
        if text.strip():
            TXT_PATH.write_text(text, encoding="utf-8")
            print(f"\n[SUCCESS] OCR done! Saved to: {TXT_PATH}")
            print(f"[INFO] Extracted {len(text)} chars")
            print(f"\nFirst 500 chars:\n{text[:500]}")
            print("\n[INFO] Bot will now use base_resume.txt automatically.")
        else:
            print("[ERROR] OCR produced empty output.")
    except Exception as e:
        print(f"[ERROR] OCR failed: {e}")
        if "tesseract" in str(e).lower():
            print("\n[INFO] Tesseract binary missing. Install:")
            print("       https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n[INFO] OR easier: create resumes/base_resume.txt manually.")


if __name__ == "__main__":
    main()
