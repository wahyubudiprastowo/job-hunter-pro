# 🔑 MASTER CONTINUITY DOCUMENT (v3.1)

> **READ ME FIRST.** This is the single source of truth for picking up the project.

---

## 🎯 Project Identity
- **Name**: Job-Hunter Pro
- **Repository**: 
  - GitLab (primary): https://gitlab.com/1bulan1m/job-hunter-pro
  - GitHub (public mirror): https://github.com/wahyubudiprastowo/job-hunter-pro
- **Owner**: Wahyu Budi Prastowo (IT Infrastructure Specialist)
- **Target**: Automate LinkedIn (+ multi-platform) job applications for EU Cloud/DevOps roles
- **Local path**: `C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\`
- **Web UI**: http://localhost:5050

---

## 📸 Last Known Good State (v3.1 snapshot)

| Indicator | Value |
|---|---|
| Bot State | Stable, daily production use |
| Cumulative Applied | 50+ confirmed via Gmail |
| Per-run Applied | 6-10 typically |
| Saved Answers | 138+ entries |
| Tailored per run | 5-9 (35% reject rate) |
| CV Length | 6023 chars (82 tech terms) |
| Languages Supported | 8 (EN/IT/ES/FR/DE/NL/PT/SV) |
| Patches Applied | 1-15 (all documented) |

---

## 🧬 Current Patch Status

| Patch | Source | Status |
|---|---|---|
| MVP, 1-3 | Copilot | ✅ Documented |
| 5-8 | External | ✅ Documented |
| 9, 9.1 | Copilot | ✅ Documented |
| 10 | Copilot | ✅ Documented (Phase 2c PARTIAL) |
| 11 | Copilot | ✅ Documented (6 bugs fixed) |
| 12 | Copilot | ✅ Documented (validator expansion) |
| 13 | Copilot | ✅ Documented (Easy Apply 5-strategy) |
| **14** | **User** | **✅ Documented (already-applied detection)** |
| **15** | **User** | **✅ Documented (CV header phone/links)** |

---

## 🚦 Read This Order
1. THIS file
2. [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
3. [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
4. [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md) ⭐ NEW v3.1
5. [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md) ⭐ NEW v3.1
6. [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)
7. [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md)

---

## 🚨 CRITICAL Rules
1. ✅ Apply patches via `apply.cmd` (auto-backup) OR user direct edit with git commit
2. ✅ Test on throwaway account first
3. ❌ NEVER touch `.chrome-profile/`, `.env`, working selectors
4. ❌ NEVER reduce acceptance criteria
5. ❌ NEVER hardcode API keys in config.yaml
6. ✅ ALWAYS use `.env` for secrets

---

## 🛠️ Quick Start
```powershell
cd C:\Users\WP2300419\Documents\VContainer
git clone https://github.com/wahyubudiprastowo/job-hunter-pro.git
cd job-hunter-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: LINKEDIN_EMAIL, LINKEDIN_PASSWORD, AI_API_KEY, AI_BASE_URL
python run_web.py
```

---

## 🎯 What's Next After Patch 15
1. **Patch 16**: Cover Letter LinkedIn Upload (Phase 2c → DONE)
2. **Patch 17**: Phase 2d Fit Scoring  
3. **Patch 18**: UI/UX improvements (timezone, stats)
4. **Patch 19**: Phase 3a Ghosting Detector
5. **Patch 20**: Phase 4a Indeed Extractor

See [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md) for detailed plan.

---

**Document Version**: 3.1
**Created**: 2026-06-24
**Patches covered**: 0-15 (all documented + verified)
