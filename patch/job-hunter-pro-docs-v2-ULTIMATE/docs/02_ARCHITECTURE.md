# 🏛️ Architecture

## Layered View
```
┌─────────────────────────────────────────────┐
│ PRESENTATION                                │
│ Flask Web UI + REST API (P4)                │
├─────────────────────────────────────────────┤
│ ORCHESTRATION                               │
│ Worker Runner + Pause/Resume/Stop + Heartbeat│
├──────────┬──────────┬───────────────────────┤
│ DOMAIN   │ STORAGE  │  AI LAYER             │
│ Filters  │ SQLite   │  Provider             │
│ Quest Bot│ JSON     │  Question Bot         │
│ Tailor   │ Logs     │  Resume Tailor (2b)   │
│ Scorer   │          │  Fit Scorer (2d)      │
├──────────┴──────────┴───────────────────────┤
│ PLUGIN — BaseExtractor                      │
│ LinkedIn (P1) Indeed (P4) Glassdoor (P4)... │
├─────────────────────────────────────────────┤
│ INFRA — undetected-cd, humanizer, CAPTCHA   │
└─────────────────────────────────────────────┘
```

## Apply Flow
```
START
 → load_config / answers / profile
 → init AI provider
 → init driver (stealth Chrome)
 → FOR EACH platform:
    → login()
    → FOR EACH query:
       → search() / collect_job_cards()
       → FOR EACH card:
          → pre-filters (cheap)
          → open_job_detail()
          → post-filters
          → (P2d) fit_score check → skip if low
          → (P2b) tailor resume
          → (P2c) generate cover letter
          → apply()
          → record_application()
          → human_sleep()
END
```

## Plugin Architecture
Orchestrator only calls 6 abstract methods:
```python
extractor.login(email, password, totp)
extractor.search(filters)
extractor.collect_job_cards()
extractor.open_job_detail(card)
extractor.can_auto_apply(job)
extractor.apply(job, resume_path, mode)
```

## Control Plane (file-based)
- `data/.control/state.txt` — current state
- `data/.control/command.txt` — pending command
- `data/.control/heartbeat.txt` — worker liveness (Patch 6-7)

## AI Integration Points
| Use case | Phase | Module |
|---|---|---|
| Question answering | 2a ✅ | `question_bot.py` |
| Resume tailoring | 2b 🟡 | `resume_tailor.py` |
| Cover letter | 2c ⏭️ | `cover_letter.py` |
| Job fit scoring | 2d ⏭️ | `scorer.py` |
| Ghosting analysis | 3a ⏭️ | `ghosting.py` |
| Health score | 3b ⏭️ | `health.py` |
| Interview prep | 3c ⏭️ | `interview.py` |

## Persistence
| What | Where |
|---|---|
| Applications | SQLite `data/applications.db` |
| Answer bank | `data/answers.json` (121 entries) |
| Unanswered | `data/unanswered.json` |
| Logs | `data/logs/bot.log` |
| Screenshots | `data/screenshots/` |
| Tailored resumes | `resumes/generated/` |
| Chrome session | `.chrome-profile/` |

## 🔗 Related
- [05_PLUGIN_SPEC.md](05_PLUGIN_SPEC.md)
- [07_AI_SPEC.md](07_AI_SPEC.md)
- [04_DATA_MODELS.md](04_DATA_MODELS.md)
