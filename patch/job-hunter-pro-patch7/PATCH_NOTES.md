# 🩹 PATCH 7 — CV Multi-Format + OCR Fallback

## 🎯 Issue yang Difix

CV PDF kamu **image-based** (scan/export image), bukan text-based.
- `Test-Path` return True ✅
- Size 1.6 MB, 4 pages ✅
- `extract_text()` return **empty** ❌ → AI fallback ke config facts only

## ✅ Apa yang Berubah

PATCH 7 nambah:
1. **Multi-format support**: PDF, DOCX, TXT auto-detect
2. **TXT sibling check**: kalau `base_resume.pdf` gak bisa, otomatis cek `base_resume.txt`
3. **OCR fallback**: kalau `pdf2image` + `pytesseract` installed, auto-OCR image PDF
4. **Helper script**: `convert_cv_to_text.py` untuk diagnose + convert
5. **Sample template**: `base_resume.txt.SAMPLE` siap edit

## 📁 Files

| File | What |
|---|---|
| `packages/ai/cv_extractor.py` | REPLACED — multi-format + OCR support |
| `convert_cv_to_text.py` | NEW helper at project root |
| `base_resume.txt.SAMPLE` | Template untuk text-based CV |

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch7
apply.cmd
```

## 🛠️ Pilih Solusi (3 opsi)

### ⭐ OPTION A: Re-export PDF (1 menit, paling recommended)

CV kamu pasti ada source Word/Docs. Re-export sebagai text-based:

**Word**:
- File → Save As → PDF
- Click "More options" → "Options..."
- ❌ Uncheck: "ISO 19005-1 compliant (PDF/A)"
- ❌ Uncheck: "Bitmap text when fonts may not be embedded"
- Save

**Google Docs**:
- File → Download → PDF Document (.pdf)

**Canva**:
- Download → PDF Standard (NOT PDF Print)

Lalu copy ke `resumes\base_resume.pdf`.

Test:
```powershell
python -c "import pypdf; print(pypdf.PdfReader('resumes/base_resume.pdf').pages[0].extract_text()[:500])"
```

Kalau muncul text "Wahyu Budi..." → ✅ siap.

### 🔍 OPTION B: OCR (kalau cuma punya scan)

```powershell
# Install OCR libs
pip install pdf2image pytesseract Pillow

# Install Tesseract binary (one-time)
# Download: https://github.com/UB-Mannheim/tesseract/wiki
# Install ke default location: C:\Program Files\Tesseract-OCR\

# Run helper to OCR + convert to TXT
python convert_cv_to_text.py
```

Helper akan:
1. Cek PDF text extraction
2. Kalau empty → run OCR
3. Save hasil ke `resumes\base_resume.txt`
4. Bot otomatis baca TXT next run

### ⚡ OPTION C: Manual TXT (FASTEST)

1. Buka `base_resume.txt.SAMPLE` (di folder patch ini) di Notepad
2. Edit dengan isi CV asli kamu — terutama tech skills + years
3. Save As → `resumes\base_resume.txt`

**Penting yang harus akurat:**
```
- Microsoft Azure: 8 years
- Kubernetes: 3 years        ← angka REAL kamu
- Linux: 8 years              ← angka REAL kamu
- CommVault: 0 years          ← kalau gak punya, tulis 0
```

Bot prioritas: `base_resume.txt` → kalau ada, langsung pakai (skip PDF).

## 🧪 Verifikasi

Setelah pilih salah satu option di atas, test:

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
.\.venv\Scripts\Activate.ps1

# Test extract via bot code
python -c "from packages.ai.cv_extractor import extract_cv_text; t=extract_cv_text('resumes/base_resume.pdf'); print('OK:' if t and len(t)>100 else 'FAIL:', len(t) if t else 0, 'chars')"
```

Expected: `OK: 4523 chars` (atau angka berapa pun > 100)

Lalu restart bot:
```powershell
python run_web.py
```

Log harusnya nampilin:
```
SUCCESS | 📄 Loaded CV: 4523 chars from resumes/base_resume.pdf
```

(Atau `📄 Loaded CV from TXT: resumes/base_resume.txt` kalau pakai Option C)

## 🎯 Result Setelah Fix

Sekarang AI bakal jawab pertanyaan **berdasarkan CV asli**:

```
INFO | 🤖 AI answered '8' for: How many years with Azure   ← dari CV
INFO | 🤖 AI answered '3' for: How many years with Kubernetes  ← dari CV
INFO | 🤖 AI answered '0' for: How many years with CommVault  ← gak di CV = honest
INFO | 🤖 AI answered 'Elementary' for: Italian proficiency  ← dari CV
INFO | ✅ APPLIED [Cloud Engineer @ Triskel Consulting]
```

Tidak ada lagi "Linux 10 years" yang ngarang. 🎉
