# 📸 Current State Snapshot

What is **actually running in production right now**. Last verified: 2026-06-24.

---

## 🖥️ Dashboard Live State

```
┌────────────────────────────────────────────────────────────┐
│  🤖 Job-Hunter Pro              State: RUNNING            │
├────────────────────────────────────────────────────────────┤
│  [🚀 Start] [⏸ Pause] [▶ Resume] [🛑 Stop]              │
│  [🔄 Reset State] [🧪 Test AI]                            │
├────────────────────────────────────────────────────────────┤
│  🔧 Diagnostics                                            │
│  State        : running                                    │
│  Command      : (none)                                     │
│  PID          : 34036                                      │
│  Heartbeat age: 3.1s                                       │
│  Is zombie    : No                                         │
├────────────────────────────────────────────────────────────┤
│  Applied: 18  Skipped: 47  Needs: 7  Failed: 6  Ext: 0   │
├────────────────────────────────────────────────────────────┤
│  Live Logs (last 100 lines)                                │
│  ...run_bot:284 — 🎉 Run done.                            │
│  Counters: {'applied': 9, 'skipped': 38, 'failed': 0,     │
│             'needs': 0, 'tailored': 0}                    │
└────────────────────────────────────────────────────────────┘
```

---

## ✅ Confirmed Working Features

### Phase 1 (MVP) — All ✅
- Plugin BaseExtractor architecture
- LinkedIn login (with cached session via `.chrome-profile/`)
- LinkedIn search with EU filters
- Job card collection (lazy scroll, dedupe)
- Detail page extraction
- Easy Apply modal walking
- Pause/Resume/Stop control
- SQLite history
- Flask web dashboard
- Multi-language buttons (EN/IT/ES/FR/DE/PT/NL)
- Stuck detection (same progress 2x → abort)
- Save dialog auto-Discard
- Multi-strategy submit verification
- Debug screenshots on failure
- Auto-decline diversity questions

### Phase 2a (AI Question Fallback) — ✅ Hot in production
- AIProvider (OpenAI-compatible, custom base_url support)
- Question fallback when answer bank misses
- Auto-save AI answers (currently **121 saved answers**)
- Multi-language Q&A (Italian, German, Portuguese in bank visible)
- Cooldown on AI failure (300s)

### Phase 2b (Resume Tailoring) — 🟡 Infrastructure present, output=0
- Counter `tailored` in RunHistory ← exists
- Likely files: `packages/ai/resume_tailor.py`
- Likely config flag: `ai.resume_tailoring: bool`
- Likely output dir: `resumes/generated/`
- **`tailored: 0`** in last run suggests: feature disabled OR not triggering OR validator rejecting all

### New UI features (from Patch 4-8, undocumented)
- **🔄 Reset State button** — clears stuck state files
- **🧪 Test AI button** — pings AI provider, shows status
- **🔧 Diagnostics card** — PID, heartbeat, zombie detection
- **Heartbeat mechanism** — worker writes timestamp every N seconds
- **Zombie detection** — flags worker as dead if heartbeat too old

---

## 📂 Inferred File Structure (Production Repo)

Based on screenshot + GitLab repo:
```
job-hunter-pro/
├── apps/
│   ├── web/
│   │   ├── app.py                  ← extended with Reset/Test AI/Diagnostics endpoints
│   │   └── templates/
│   │       ├── dashboard.html       ← includes Diagnostics card
│   │       ├── applications.html
│   │       ├── application_detail.html
│   │       └── questions.html
│   └── worker/
│       ├── runner.py               ← may include heartbeat writer
│       └── control.py              ← extended with reset() + heartbeat
├── packages/
│   ├── core/
│   │   ├── models.py
│   │   ├── filters.py
│   │   └── exceptions.py
│   ├── extractors/
│   │   ├── base.py
│   │   └── linkedin.py             ← may include tailored resume upload
│   ├── ai/
│   │   ├── provider.py
│   │   ├── question_bot.py
│   │   └── resume_tailor.py        ← Phase 2b (likely exists)
│   ├── stealth/
│   │   ├── browser.py              ← may have startup speed fixes
│   │   └── humanizer.py
│   └── storage/
│       ├── db.py
│       └── answers.py
├── config.yaml                      ← has ai.resume_tailoring flag
├── data/
│   ├── applications.db
│   ├── answers.json                 ← 121 entries
│   ├── unanswered.json              ← 1 entry
│   ├── logs/bot.log
│   ├── screenshots/
│   └── .control/
│       ├── state.txt
│       ├── command.txt
│       └── heartbeat.txt           ← NEW
├── resumes/
│   ├── base_resume.pdf
│   └── generated/                   ← Phase 2b output dir
└── docs/                            ← will become THIS bundle
```

---

## 🔍 What to Verify After Reading

Run these to confirm state matches this snapshot:

```powershell
# 1. Files exist
Get-ChildItem packages\ai
Get-ChildItem patch | Select-Object Name

# 2. AI is working (Test AI button or):
curl http://localhost:5050/api/state

# 3. Saved answers count
python -c "import json; print(len(json.load(open('data/answers.json'))))"

# 4. Last run summary
Get-Content data\logs\bot.log | Select-String "Counters" | Select-Object -Last 1

# 5. Tailored resumes exist?
Get-ChildItem resumes\generated -ErrorAction SilentlyContinue
```

If outputs match snapshot → continuity confirmed. If different → update this doc.

---

## ⚠️ Known Unknowns

Things in production we don't have source for in this docs bundle:

1. **Exact code in `packages/ai/resume_tailor.py`** — need to read from repo
2. **Exact heartbeat implementation** — need to read `apps/worker/control.py`
3. **Exact diagnostics endpoint** — need to read `apps/web/app.py`
4. **Reset State endpoint logic**
5. **Test AI endpoint logic**
6. **config.yaml current state** (post-patches)

### How to fill these gaps
See [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) → "Reverse-Engineering Protocol".

---

## 📊 Production Metrics

From observable dashboard:
- **Real applications submitted to EU**: 18 across 5 days
- **Question bank growth rate**: ~24 entries/day (auto-learned)
- **Skip rate**: 47/(47+18+6) = 66% (high but expected with strict filters)
- **AI fallback usage**: ~80% of new questions get AI-answered
- **Zero hallucinations reported** by user

---

## 🔗 Related
- [00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md) — first read
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) — patch ancestry
- [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md) — what to preserve
