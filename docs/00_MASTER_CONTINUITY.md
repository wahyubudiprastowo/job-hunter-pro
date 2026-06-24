# Master Continuity Document

Read this first. It is the fastest safe handoff file for continuing work on the project.

## Project Identity

- Name: Job-Hunter Pro
- Owner: Wahyu Budi Prastowo
- Target: automate LinkedIn-first job applications for Cloud, Infrastructure, and DevOps roles
- Local path: `C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\`
- Web UI: `http://localhost:5050`
- Primary repos:
  - GitLab: https://gitlab.com/1bulan1m/job-hunter-pro
  - GitHub: https://github.com/wahyubudiprastowo/job-hunter-pro

## Last Known Working State

As of 2026-06-24:

| Indicator | Value |
|---|---|
| Bot state | running in active local use |
| Total applied | 50+ cumulative |
| Saved answers | 138+ |
| Tailored resumes | active |
| Cover letter upload | integrated |
| Fit scoring | code integrated but disabled by config |
| Languages | 8 |
| Current docs scope | merged active docs plus selective v3.3 additions |

## Current Reality

- Patch 16 cover letter upload is implemented.
- Patch 17 fit scoring is implemented conservatively in code, but `fit_scoring` is still `false` in `config.yaml`.
- Dashboard and LinkedIn flow received additional operational fixes after the original docs merge:
  - live `Latest Run` progress updates
  - tighter external classification
  - stronger Easy Apply button lookup/click fallback
- A LinkedIn rate-limit incident was documented on 2026-06-24. Treat that as important operational context, but do not assume the account is still in cooldown unless current logs or UI confirm it.

## Read Order

1. This file
2. [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
3. [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
4. [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
5. [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md)
6. [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md)
7. [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)
8. [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md)

## Critical Rules

1. Read the existing code before changing behavior.
2. Prefer targeted fixes. Do not do large refactors unless explicitly requested.
3. Do not touch `.chrome-profile/`, `.env`, or working selectors casually.
4. Keep acceptance behavior that already works in production.
5. Use `.env` for secrets.
6. Update docs when a real patch lands.
7. If imported docs conflict with the repo state, trust verified repo state.

## Current Patch Reality

- Patches 1-15 are implemented and documented.
- Patch 16 and 16.1 are implemented and documented.
- Patch 17 is partially validated: code and DB integration landed, runtime smoke test still pending with `fit_scoring: true`.
- Patch 18 dashboard UX changes landed.
- The next major planning artifact added from the v3.3 bundle is [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md).

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
6. If it smells like account throttling or rate limiting, read [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md).

## Next Focus

1. Validate Patch 17 on a small real run when ready.
2. Patch 19 Smart Rate Limiter.
3. Patch 20 Ghosting Detector.
4. Patch 21 UI modernization.
