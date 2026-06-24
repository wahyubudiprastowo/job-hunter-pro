# 🏛️ Architecture (Phase 1)

## Layered View

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│           Flask (apps/web/app.py)  +  Templates              │
│           Pause / Resume / Stop buttons                      │
│           Live log tail (5s polling)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / file signals
┌─────────────────────────▼───────────────────────────────────┐
│                   ORCHESTRATION LAYER                        │
│           apps/worker/runner.py                              │
│           apps/worker/control.py                             │
│           (loops platforms → queries → cards → apply)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────────────┐
        ▼                 ▼                         ▼
┌──────────────┐ ┌──────────────────┐  ┌──────────────────┐
│  Extractors  │ │   Core / Models  │  │     Storage      │
│  (plugins)   │ │ (Pydantic, filt.)│  │  SQLite + JSON   │
└──────────────┘ └──────────────────┘  └──────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│  Stealth Layer                       │
│  undetected-chromedriver +           │
│  human_sleep + type_human            │
└──────────────────────────────────────┘
```

## Apply Flow (End-to-End)

```
START
 ├── load_config() (config.yaml)
 ├── load_answers()
 ├── CandidateProfile(**config.personal)
 ├── build_driver()                       # Stealth Chrome
 │
 ├── FOR EACH enabled platform:
 │    ├── extractor = ExtractorClass(driver, cfg, profile, answers, stealth)
 │    ├── extractor.login(email, pass, totp)
 │    │
 │    ├── FOR EACH search query:
 │    │    ├── extractor.search(filters)         # navigates to results URL
 │    │    ├── cards = extractor.collect_job_cards()
 │    │    │
 │    │    └── FOR EACH card:
 │    │         ├── PRE-FILTERS (cheap, before opening detail):
 │    │         │     ├── company_passes()
 │    │         │     ├── title_passes()
 │    │         │     └── already_applied()
 │    │         │
 │    │         ├── job = extractor.open_job_detail(card)
 │    │         │
 │    │         ├── POST-FILTERS (after detail loaded):
 │    │         │     ├── description_passes()
 │    │         │     ├── salary_passes()
 │    │         │     └── can_auto_apply()
 │    │         │
 │    │         ├── result = extractor.apply(job, resume_path, mode)
 │    │         │
 │    │         ├── store.record_application(job, result)
 │    │         ├── add_unanswered(result.unanswered_questions)
 │    │         │
 │    │         ├── controller.check()    # pause/stop?
 │    │         └── human_sleep()         # anti-detect
 │    │
 │    └── extractor.close()
 │
 └── driver.quit()
```

## Why a Plugin Architecture?

**The orchestrator never imports LinkedIn-specific anything.** All it knows is:

```python
extractor.login(...)
extractor.search(filters)
extractor.collect_job_cards()
extractor.open_job_detail(card)
extractor.can_auto_apply(job)
extractor.apply(job, resume_path, mode)
```

This is the **Open-Closed Principle** in action:
- Open for extension: drop in `indeed.py`, `glassdoor.py`, `jobstreet.py`
- Closed for modification: orchestrator + UI + storage never change

## Data Model

### `Application` (SQLite)
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `platform` | str | `linkedin`, `indeed`, ... |
| `job_id` | str | unique, deduplicates |
| `title`, `company`, `location` | str | |
| `url`, `salary`, `description` | text | |
| `status` | enum | `applied` / `skipped` / `failed` / `needs_answers` / `external` |
| `skip_reason` | enum | `blacklisted_company`, `excluded_keyword`, etc. |
| `error_message` | text | |
| `resume_path`, `cover_letter_path` | str | |
| `qa_log_json` | JSON | full Q&A trail |
| `unanswered_json` | JSON | questions bot couldn't answer |
| `created_at` | datetime | |

### `RunHistory`
| Column | Type |
|---|---|
| `id`, `started_at`, `finished_at` | |
| `applied`, `skipped`, `failed`, `needs_answers` | int counters |
| `notes` | text |

## Files vs DB

| What | Where | Why |
|---|---|---|
| Applications | SQLite (`data/applications.db`) | Queryable, indexable |
| Answer bank | `data/answers.json` | Easy to edit by hand |
| Unanswered queue | `data/unanswered.json` | Easy to inspect & edit |
| Control signals | `data/.control/*.txt` | Simple, no Redis dep |
| Logs | `data/logs/bot.log` | Rotating, tail-friendly |
| Chrome profile | `.chrome-profile/` | Cached cookies for login |
