# Master Continuity Document

Read this first. It is the fastest safe handoff file for continuing work on the project.

## Project Identity

- Name: Job-Hunter Pro
- Owner: Wahyu Budi Prastowo
- Target: automate job applications for EU Cloud, Infrastructure, and DevOps roles
- Local path: `C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\`
- Web UI: `http://localhost:5050`
- Primary repos:
  - GitLab: https://gitlab.com/1bulan1m/job-hunter-pro
  - GitHub: https://github.com/wahyubudiprastowo/job-hunter-pro

## Last Known Good State

As of 2026-06-24:

| Indicator | Value |
|---|---|
| Bot state | stable and used in production |
| Total applied | 50+ cumulative |
| Typical per run | 6-10 applied |
| Saved answers | 138+ |
| Tailored resumes | active |
| CV quality | country code phone and profile links fixed |
| Languages | 8 |
| Patch coverage | 1-15 documented in active docs |

## Read Order

1. This file
2. [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
3. [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
4. [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
5. [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md)
6. [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)
7. [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md)

## Critical Rules

1. Read the existing code before changing behavior.
2. Prefer targeted fixes. Do not do large refactors unless explicitly requested.
3. Do not touch `.chrome-profile/`, `.env`, or working selectors casually.
4. Keep acceptance behavior that already works in production.
5. Use `.env` for secrets.
6. Update docs when a real patch lands.

## Current Patch Reality

- Patches 1-3: foundational LinkedIn and AI answer flow.
- Patches 5-8: operational/dashboard and tailoring capabilities already present in repo.
- Patches 9-13: validator, cover letter, and detection improvements.
- Patch 14: already-applied detection.
- Patch 15: CV header phone and link fix.

See [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for the authoritative patch log.

## Quick Start

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_web.py
```

## If Something Breaks

1. Stop the bot from the UI.
2. Check `data/logs/bot.log`.
3. Check `data/screenshots/`.
4. Read [16_TROUBLESHOOTING.md](16_TROUBLESHOOTING.md).
5. Check recent code and doc changes before patching further.

## Next Focus

1. Patch 17: fit scoring
2. Patch 18: UI and dashboard correctness
3. Patch 19: ghosting detector
4. Patch 20: Indeed extractor

