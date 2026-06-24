# ⚙️ Configuration Specification

## config.yaml — Full Reference

### Top-level
- `mode`: `full_auto` | `semi_auto` | `safe_auto`

### platforms.<name>.*
- `enabled`, `max_apply_per_run`
- `search.queries`, `location`, `remote`, `hybrid`
- `search.date_posted`, `experience_levels`, `job_type`
- `search.easy_apply_only`

### filters.*
- `title_keywords_include`, `title_keywords_exclude`
- `description_keywords_exclude`
- `company_blacklist`
- `min_salary`
- `skip_already_applied`

### personal.* (CandidateProfile)
All fields user-editable. See `packages/core/models.py::CandidateProfile`.

### resume.*
- `default_path`: base CV PDF
- `base_text_path`: plain-text for AI (P2b)

### ai.*
See [07_AI_SPEC.md](07_AI_SPEC.md).

### stealth.*
- `min_delay_sec`, `max_delay_sec`
- `typing_min_delay`, `typing_max_delay`
- `pause_every_n_applications`, `pause_seconds`

### global_limits.*
- `total_apply_per_day`
- `total_apply_per_run`

### scheduler.* (Phase 3d)
- `enabled`, `schedules: [{name, cron, timezone, ...}]`

### notifications.* (Phase 3d)
- `telegram`, `email`, `teams`, `discord`, `webhook`

## .env

```env
# LinkedIn (P1)
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
LINKEDIN_TOTP_SECRET=

# AI (P2)
AI_API_KEY=
AI_BASE_URL=

# Web
FLASK_SECRET_KEY=
WEB_HOST=0.0.0.0
WEB_PORT=5050

# Browser
HEADLESS=false
USER_DATA_DIR=./.chrome-profile
CHROME_VERSION_MAIN=

# Phase 3
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TWO_CAPTCHA_KEY=

# Phase 4 (per platform)
INDEED_EMAIL=
INDEED_PASSWORD=
GLASSDOOR_EMAIL=
GLASSDOOR_PASSWORD=
JOBSTREET_EMAIL=
JOBSTREET_PASSWORD=
```

## Validation
Config validated via Pydantic on start. Errors fail loud.

## 🔗 [11_SECURITY_PRIVACY.md](11_SECURITY_PRIVACY.md) — why .env over yaml for secrets
