# 🩹 PATCH 6 — CV-Powered AI Answers (Anti-Hallucination Final)

## 🎯 Problem yang Difix

Dari log + screenshot kemarin:

| Issue | Sebelumnya | Sekarang |
|---|---|---|
| Bot ngarang "Linux 10, VMware 10" — gak baca CV | ❌ Tebakan dari config | ✅ Baca CV PDF → AI jawab dari CV |
| AI gagal koneksi dengan error aneh "base_url=cgpt-web/gpt-5.4-pro" | ❌ Config corrupt | ✅ Validasi URL on startup |
| Tidak ada cara bot tahu skill real kamu | ❌ Cuma config personal | ✅ Full CV text masuk ke AI prompt |
| Bot tetep apply walau jawaban salah → wasted apply | ❌ Submit dengan invented numbers | ✅ AI fallback jawab dari CV truth |

## 🧠 Cara Kerja Baru

```
Saat bot start:
1. Baca config.yaml → personal info
2. Baca resumes/base_resume.pdf → extract semua text
3. Build "candidate facts" = config + CV text
4. AI system prompt include FULL CV content

Saat ketemu question (contoh: "Years with Linux?"):
1. Cek answer bank
2. Cek personal info map
3. Cek fuzzy match
4. AI FALLBACK:
   - System prompt include CV
   - AI baca CV, cari "Linux" → calculate years dari tahun pertama mention
   - Return real number (atau "0" kalau gak ada)
5. Save jawaban ke answer bank
```

**Tidak ada lagi tebakan.** AI jawab berdasarkan CV asli kamu.

## 📁 Files

| File | What |
|---|---|
| `packages/ai/cv_extractor.py` | NEW — Read PDF, extract text, build enriched facts |
| `packages/ai/question_bot.py` | REPLACED — Stronger prompt with CV reference |
| `packages/extractors/linkedin.py` | PATCHED in-place by `patch_linkedin.py` |
| `apps/worker/runner.py` | REPLACED — Load CV + validate AI config + pass cv_text |
| `patch_linkedin.py` | Helper script that patches linkedin.py inline |
| `apply.cmd` | Auto-installer |

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch6
apply.cmd
```

Auto-installer:
1. Backup ke `.backup_p6_<timestamp>/`
2. Copy new files
3. Run `patch_linkedin.py` to add `cv_text` param to extractor
4. Auto-install `pypdf` package
5. Print next steps

## ⚠️ KRITIKAL: Fix `.env` File Kamu

Dari log kamu kemarin, `.env` ada masalah format. Log nampilin:
```
base_url=cgpt-web/gpt-5.4-pro          ← SALAH
base_url=antigravity/gemini-3.5-flash-medium  ← SALAH (itu nama model, bukan URL)
```

Buka `.env` di Notepad, **pastikan EXACT** seperti ini:

```env
LINKEDIN_EMAIL=email_kamu
LINKEDIN_PASSWORD=password_kamu
HEADLESS=false
WEB_PORT=5050

AI_API_KEY=
AI_BASE_URL=https://openwebui.tail443aaa.ts.net/api/v1/vscode/sk-3d39a725ffa5e05f-539a83-9e66c5a9
```

**Cek**:
- ❌ Tidak ada spasi di awal baris
- ❌ Tidak ada tanda kutip (`"` atau `'`)
- ✅ URL pakai `https://`
- ✅ URL ada full path sampai `/sk-3d39a725ffa5e05f-539a83-9e66c5a9` (tanpa `/chat/completions` di akhir)

## 📄 Pastikan CV Ada

```powershell
ls C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\resumes\base_resume.pdf
```

Kalau gak ada → copy CV PDF kamu ke folder itu.

## 🧪 Test Setelah Patch

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
.\.venv\Scripts\Activate.ps1
python run_web.py
```

Buka http://localhost:5050:

1. **Klik 🧠 Test AI**
   - ✅ AI works: 'ready' → siap
   - ❌ 401 → key salah / URL salah
   - ❌ Connection failed → Tailscale putus

2. **Klik 🚀 Start**

Lihat log, harusnya muncul:
```
INFO | 📄 Extracted CV (4250 chars) using pypdf
SUCCESS | 📄 Loaded CV: 4250 chars from resumes/base_resume.pdf
INFO | 🧠 AI provider ready: model=..., base_url=https://openwebui...
SUCCESS | 🧠 AI connection test: OK: 'ready'
INFO | 🧠 AI question fallback enabled.
...
INFO | 🤖 AI answered '8' for: How many years with Linux
INFO | 💾 Saved AI answer
INFO | 🤖 AI answered '0' for: How many years with CommVault
INFO | 💾 Saved AI answer
INFO | ✅ APPLIED [...]
```

## 🛡️ Anti-Hallucination Guards

System prompt baru explicit:
- "If X is NOT mentioned in CV → answer '0'"
- "NEVER invent years"
- "Read the CV carefully"

Plus:
- AI cuma baca dari `candidate_facts` (yang include CV)
- Format strict: number only / Yes-No only / option only
- "UNKNOWN" escape hatch kalau AI bingung

## 🐛 Troubleshooting

### "Could not extract CV"
- Cek file ada di `resumes\base_resume.pdf`
- CV harus PDF text-based (bukan scan/image PDF)
- Coba: `python -c "import pypdf; print(pypdf.PdfReader('resumes/base_resume.pdf').pages[0].extract_text()[:500])"`

### AI test masih 401 setelah update .env
- Token endpoint mungkin udah expired
- Generate ulang VS Code Token Alias di OmniRouter
- Atau test direct: `curl.exe https://openwebui.tail443aaa.ts.net/api/v1/vscode/sk-.../models`

### AI test "Connection error"
- Tailscale disconnect → connect ulang
- Test: `ping openwebui.tail443aaa.ts.net`

### linkedin.py patch failed (no changes applied)
- File mungkin udah dipatch sebelumnya
- Atau format berubah karena patch sebelumnya
- Manual fix: edit `packages/extractors/linkedin.py`, tambah `cv_text=None` ke `__init__` parameters

## 🎯 Expected Result

```
2026-06-24 02:00:00 | SUCCESS | 📄 Loaded CV: 4523 chars
2026-06-24 02:00:01 | SUCCESS | 🧠 AI connection test: OK: 'ready'
2026-06-24 02:00:15 | INFO    | 🤖 AI answered '8' for: How many years with Linux
2026-06-24 02:00:16 | INFO    | 💾 Saved AI answer
2026-06-24 02:00:17 | INFO    | 🤖 AI answered '5' for: How many years with VMware
2026-06-24 02:00:18 | INFO    | 🤖 AI answered '0' for: How many years with CommVault  
2026-06-24 02:00:25 | SUCCESS | ✅ APPLIED [Cloud Engineer @ ELCIA Group]
```

Bot apply dengan **angka REAL dari CV kamu**, bukan tebakan ku. Jadi:
- Linux: AI baca CV, cari "Linux" + tahun → e.g., "8"
- CommVault: AI gak nemu di CV → "0" (honest)
- Spanish proficiency: AI gak nemu Spanish di CV → "Elementary"
