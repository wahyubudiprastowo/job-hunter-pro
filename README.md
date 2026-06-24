# Job-Hunter Pro

LinkedIn Easy Apply automation bot with a local Flask dashboard, SQLite history, answer bank, AI-assisted resume tailoring, cover letter generation, fit scoring, and a DB-backed smart rate limiter.

This repository is no longer just "Phase 1". The active codebase already includes the core LinkedIn flow plus several Phase 2 and Patch 19 capabilities. The `docs/` folder is the canonical source of truth; this root README is the practical quick-start and feature summary.

> Warning: Automating LinkedIn may violate their User Agreement. Use a test account first and accept the risk yourself.

---

## Current Status

### Live in the repo now

| Area | Status |
|---|---|
| Plugin-style extractor architecture | Done |
| LinkedIn login -> search -> Easy Apply | Done |
| Multi-language Easy Apply detection | Done |
| Already-applied detection | Done |
| External apply separation | Done |
| Answer bank + unanswered queue | Done |
| Resume tailoring | Done |
| Cover letter generation | Done |
| Cover letter upload when field exists | Done |
| Fit scoring before apply | Integrated |
| Dashboard controls + history + diagnostics | Done |
| Latest Run live progress | Done |
| Debug screenshot surfacing | Done |
| Smart rate limiter + dashboard reset control | Integrated |
| CSV export for applications | Done |

### Not implemented yet

| Area | Status |
|---|---|
| Indeed extractor | Integrated in code, disabled by default, live validation pending |
| Glassdoor / JobStreet extractors | Planned |
| Ghosting detector | Planned |
| Health score backend | Planned |
| Interview prep backend | Planned |
| Notifications scheduler/channels | Planned |
| CAPTCHA solver | Integrated in code, disabled by default, live validation pending |

---

## Quick Start

### Option A - Docker

```bash
# 1) Configure secrets
cp .env.example .env

# 2) Review config
nano config.yaml

# 3) Place your base resume
cp /path/to/resume.pdf resumes/base_resume.pdf

# 4) Start services
docker compose up --build -d
```

Open `http://localhost:5050`.

### Option B - Native Windows / PowerShell

Use the project venv, not your global Python:

```powershell
.\scripts\run_local.ps1
```

Or manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_web.py
```

### Option C - Native Linux/macOS

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

### Important interpreter note

If `python run_web.py` fails with missing modules such as `loguru`, you are probably using your global interpreter instead of `.venv`.

Use:

```powershell
.\.venv\Scripts\python run_web.py
```

---

## Main Workflow

1. Load config, credentials, and base resume.
2. Login to LinkedIn with cached browser profile support.
3. Search jobs using configured filters.
4. Reject jobs by title/company/description/salary/already-applied checks.
5. Optionally score fit before spending more AI work.
6. Optionally tailor resume and generate cover letter.
7. Walk Easy Apply modal and answer questions from:
   - saved answers
   - fuzzy matching
   - AI fallback
   - unanswered queue if still unknown
8. Persist every result to SQLite and update the dashboard.

---

## Operating Modes

Set `mode:` in `config.yaml`.

| Mode | Behavior |
|---|---|
| `full_auto` | Submits automatically. |
| `semi_auto` | Stops when unknown questions need human answers. |
| `safe_auto` | Waits for manual confirmation before final submit. |

---

## AI Features

Configured under `ai:` in `config.yaml`.

Current AI-backed capabilities:

- question fallback
- resume tailoring
- tailored PDF generation
- cover letter generation (`txt` + `pdf`)
- cover letter upload if the LinkedIn form exposes a field
- fit scoring with threshold-based skip
- validation and anti-hallucination checks

Important toggles:

- `ai.enabled`
- `ai.resume_tailoring`
- `ai.cover_letter`
- `ai.fit_scoring`
- `ai.validator_strict`
- `ai.cover_letter_strict`

Environment values such as `AI_API_KEY` and `AI_BASE_URL` should live in `.env`.

---

## Dashboard

Visit `http://localhost:5050`.

Current pages:

- `Dashboard`
  - start / pause / resume / stop
  - test AI
  - reset state
  - rate limit status + reset limiter
  - KPI cards
  - latest run
  - live logs
  - debug screenshot summary
  - unanswered question summary
  - recent applications
- `Applications`
  - status filters
  - platform filter scaffold
  - CSV export
  - paginated history
  - fit score column
- `Application detail`
  - platform link
  - generated files
  - fit reasoning
  - Q&A trail
- `Questions`
  - unanswered queue
  - manual answer entry
  - saved answer bank maintenance

Note: some UI entries like Health Score, Interview Prep, and Notifications are visual scaffolds only right now; their backends are not active yet.

---

## Smart Rate Limiter

Patch 19 introduced a DB-backed limiter that tracks daily usage across runs.

Current behavior:

- daily cap awareness
- cooldown tracking
- adaptive throttle config
- dashboard visibility
- manual limiter reset from dashboard

Configured under `global_limits:` in `config.yaml`.

---

## Project Structure

```text
job-hunter-pro/
├── apps/
│   ├── web/                  # Flask dashboard
│   └── worker/               # bot runner + control plane
├── packages/
│   ├── ai/                   # provider, tailoring, cover letter, scoring
│   ├── core/                 # models, filters, exceptions
│   ├── extractors/           # base + linkedin + rate limiter
│   ├── stealth/              # browser + humanized actions
│   └── storage/              # SQLite + answer persistence
├── data/                     # SQLite, logs, unanswered queue, screenshots
├── resumes/                  # base and generated resumes
├── cover_letters/            # generated cover letters
├── docs/                     # canonical documentation
├── config.yaml
├── requirements.txt
└── run_web.py
```

---

## Documentation

Start with:

- [docs/README.md](docs/README.md)
- [docs/00_MASTER_CONTINUITY.md](docs/00_MASTER_CONTINUITY.md)
- [docs/CURRENT_STATE_SNAPSHOT.md](docs/CURRENT_STATE_SNAPSHOT.md)
- [docs/FEATURE_CHECKLIST.md](docs/FEATURE_CHECKLIST.md)
- [docs/NEXT_STEPS_ROADMAP.md](docs/NEXT_STEPS_ROADMAP.md)

Useful deep dives:

- [docs/02_ARCHITECTURE.md](docs/02_ARCHITECTURE.md)
- [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md)
- [docs/16_TROUBLESHOOTING.md](docs/16_TROUBLESHOOTING.md)
- [docs/PRDs/PRD_2d_Fit_Scoring.md](docs/PRDs/PRD_2d_Fit_Scoring.md)
- [docs/PRDs/PRD_SmartRateLimiter.md](docs/PRDs/PRD_SmartRateLimiter.md)

---

## Adding Another Platform

The orchestrator is still extractor-based. LinkedIn remains the active default flow, and the Indeed extractor is now integrated in code but disabled by default until `.env` credentials and a first manual login/captcha smoke test are completed.

Any additional platform after that should still follow `BaseExtractor` under `packages/extractors/`, then be registered in `apps/worker/runner.py`.

---

## Privacy

- local SQLite storage
- local logs
- local browser profile persistence
- no telemetry built into the app
- outbound AI calls only if AI is enabled

---

## Practical Reminder

If root docs and `docs/` ever disagree, prefer `docs/` and the current code.
