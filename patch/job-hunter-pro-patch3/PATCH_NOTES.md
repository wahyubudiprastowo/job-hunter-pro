# 🩹 PATCH 3 — Phase 2 AI Question Fallback

Bot sekarang bisa **otomatis jawab screener question** pakai AI kalau answer bank gak ketemu. Jawaban yang berhasil **otomatis di-save** untuk dipakai run berikutnya — bot belajar sendiri.

## 🐛 Issue yang Difix

| Issue | Sebelum | Setelah |
|---|:---:|:---:|
| Bot stop di question Italian/German/Portuguese yang gak ada di bank | ❌ Add ke unanswered | ✅ AI jawab → auto-save |
| 21 unanswered questions menumpuk | ❌ Manual edit semua | ✅ AI handle otomatis |
| Tidak ada cara custom AI provider | ❌ Hardcoded OpenAI | ✅ OpenAI-compatible (OmniRouter, Ollama, dll) |
| Tidak ada custom system prompt | ❌ Default only | ✅ Editable di config.yaml |
| Resume radio button list (Curriculum) tidak di-handle | ❌ Stuck | ✅ Auto-pick first |
| Placeholder option ("Seleziona", "auswählen") jadi false match | ❌ Bot kebingungan | ✅ Di-filter out |

## 📁 Files

| File | Type | Purpose |
|---|---|---|
| `packages/ai/__init__.py` | NEW | AI package init |
| `packages/ai/provider.py` | NEW | OpenAI-compatible client (works with OmniRouter, Ollama, OpenAI, DeepSeek) |
| `packages/ai/question_bot.py` | NEW | AI answers + anti-hallucination guard |
| `packages/extractors/linkedin.py` | REPLACED | + AI fallback in `_lookup_answer` |
| `apps/worker/runner.py` | REPLACED | + AI provider wiring |
| `config.yaml` | REPLACED | + `ai:` block with full settings |
| `apply.cmd` | NEW | Windows batch installer (no PS1 emoji issues!) |
| `env.append.txt` | NEW | Snippet to add to your `.env` |

## 🚀 Apply Patch (Super Easy)

Simpan patch di folder `patch/job-hunter-pro-patch3/`. Cara jalan:

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch3
apply.cmd
```

Selesai. Backup otomatis di `.backup_p3_<timestamp>/`.

## 🔧 Setup Setelah Patch

### 1. Tambah AI_API_KEY ke `.env`

Buka file `.env` di project root, tambahkan:

```env
AI_API_KEY=sk-your-actual-key-here
AI_BASE_URL=http://openwebui.tail443aaa.ts.net:20128/v1
```

> 🔒 **Penting**: jangan taro API key di `config.yaml` (mudah ke-commit ke git). Pakai `.env` yang udah ada di `.gitignore`.

### 2. Install/upgrade openai package

```powershell
.\.venv\Scripts\Activate.ps1
pip install --upgrade openai
```

### 3. Customize AI system prompt (opsional)

Buka `config.yaml`, edit block `ai.system_prompt:`. Default prompt sudah include:
- Honesty rules (no hallucination)
- Multi-language Yes/No (Sì, Oui, Ja, dll)
- Diversity auto-decline
- Language proficiency defaults
- Tech experience handling

### 4. Run

```powershell
python run_web.py
```

Lalu klik **Start** di dashboard.

## 🧠 Cara Kerja AI Fallback

```
Question dari LinkedIn form
        ↓
[1] Diversity keyword detected? → "Decline to self-identify" (FAST)
        ↓ No
[2] Match di personal info map? → return (FAST)
        ↓ No
[3] Exact match di answer bank? → return (FAST)
        ↓ No
[4] Substring match? → return (FAST)
        ↓ No
[5] Fuzzy match ≥ 85? → return (FAST)
        ↓ No
[6] AI enabled + available? → Call AI
        ↓
        AI: "Decline / Yes / No / 8 / Bachelor's Degree / UNKNOWN"
        ↓ Got real answer
[7] Auto-save to data/answers.json → use forever after
        ↓
Return answer to form filler
```

**Anti-hallucination guards**:
- System prompt forbids inventing skills/experience
- For multi-choice: AI answer fuzzy-matched to actual options (reject if < 70%)
- If AI says "UNKNOWN" → treated as no answer (no fake)
- Numeric/Yes-No format enforced

## 🎯 Expected Result

Sebelum:
```
❓ 21 unanswered questions (gender, disability, country code, language, tech experience...)
0 applied
```

Setelah:
```
INFO | 🧠 AI provider ready: model=antigravity/gemini-3.5-flash-medium, base_url=http://openwebui...
INFO | 🤖 AI answered 'Yes' for: Esperienza su infrastrutture cloud
INFO | 💾 Saved AI answer: 'esperienza su infrastrutture cloud' -> 'Yes'
INFO | 🤖 AI answered '8' for: Quanti anni di esperienza con CommVault
INFO | 💾 Saved AI answer: 'quanti anni di esperienza con commvault' -> '8'
INFO | 🤖 AI answered 'Gut' for: Wie gut beherrschen Sie Deutsch
INFO | 💾 Saved AI answer: 'wie gut beherrschen sie deutsch' -> 'Gut'
INFO | ✅ APPLIED [Cloud Engineer @ ACME EU]
INFO | ✅ APPLIED [DevOps @ SORINT.lab]
...
🎉 Run done. Counters: {'applied': 12, 'skipped': 5, 'failed': 1, 'needs': 2}
```

**Setiap apply berikutnya makin cepat** karena answer bank terus berkembang dari AI learnings.

## 🔍 Monitor AI Usage

Cek `data/logs/bot.log` untuk lines bertanda 🤖 dan 💾:
- 🤖 = AI was called
- 💾 = AI answer saved to bank

Buka `data/answers.json` untuk lihat answer bank yang udah tumbuh.

## 🛡️ Privacy

- AI client cuma kirim: question text + candidate facts (yang ada di config.yaml `personal`) + options (kalau ada)
- NO resume content sent (Phase 2b)
- NO job description sent (Phase 2c untuk fit scoring)
- NO LinkedIn credentials, NO browser cookies
- Endpoint custom: pakai OmniRouter kamu sendiri (privacy under your control)

## 🆘 Troubleshooting

### AI gak dipanggil ("AI provider ready" gak muncul di log)
- Cek `config.yaml`: `ai.enabled: true` dan `ai.question_fallback: true`
- Cek `.env`: `AI_API_KEY` ada
- Cek `pip list | findstr openai`: openai installed

### AI dipanggil tapi error
- Cek log untuk "AI call failed: ..."
- Test endpoint langsung dengan curl untuk validate base_url + key
- Kalau cooldown muncul → endpoint timeout/error, bot pause AI selama 5 menit lalu retry

### AI jawab tapi gak ke-save
- Cek `config.yaml`: `ai.auto_save_answers: true`
- Cek permission write `data/answers.json`

### Bot sekarang slow karena AI call lama
- Reduce timeout: `ai.timeout_seconds: 30`
- Atau pakai model yang lebih cepat (gemini-flash, gpt-4o-mini)
- AI dipanggil maks 1x per question — sekali jawab langsung di-cache forever
