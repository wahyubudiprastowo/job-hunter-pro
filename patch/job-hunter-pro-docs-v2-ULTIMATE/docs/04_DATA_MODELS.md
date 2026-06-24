# 📐 Data Models

Source of truth: `packages/core/models.py`.

## Enums

### ApplyStatus
- `APPLIED` — submitted
- `SKIPPED` — pre-filtered
- `FAILED` — error
- `NEEDS_ANSWERS` — unanswered questions
- `PENDING_REVIEW` — safe_auto mode
- `EXTERNAL` — non-easy-apply

### SkipReason
- `BLACKLISTED_COMPANY`
- `BLACKLISTED_TITLE`
- `EXCLUDED_KEYWORD`
- `SALARY_TOO_LOW`
- `DUPLICATE`
- `NOT_EASY_APPLY`
- `FIT_SCORE_LOW` (P2d)
- `UNKNOWN`

### GhostStatus (P3a)
- `ACTIVE` (<7d)
- `SLOW` (7-14d)
- `LIKELY_GHOSTED` (15-30d viewed not responded)
- `GHOSTED` (>30d)
- `REJECTED`
- `INTERVIEW`
- `OFFER`

## Pydantic Models

### SearchFilters
```python
queries: list[str]
location: str
remote: bool, hybrid: bool
date_posted: str
experience_levels: list[str]
job_type: str
easy_apply_only: bool
```

### JobListing
```python
platform: str, job_id: str
title: str, company: str, location: str
url: str, description: str, salary: str
is_easy_apply: bool
```

### ApplicationResult
```python
status: ApplyStatus
skip_reason: Optional[SkipReason]
qa_log: list[dict]  # {q, a, filled, options?}
unanswered_questions: list[UnansweredQuestion]
resume_path: Optional[str]
cover_letter_path: Optional[str]
fit_score: Optional[int]  # P2d
fit_reasoning: Optional[str]  # P2d
```

### CandidateProfile
See [10_CONFIGURATION_SPEC.md](10_CONFIGURATION_SPEC.md) `personal:` block.

## SQLite Schema

### applications
- id PK, platform, job_id UNIQUE
- title, company, location, url, salary, description
- status, skip_reason, error_message
- resume_path, cover_letter_path
- qa_log_json, unanswered_json
- fit_score, fit_reasoning (P2d)
- viewed_by_recruiter, last_response_at, last_response_type (P3a)
- created_at, updated_at

### run_history
- id, started_at, finished_at
- applied, skipped, failed, needs_answers
- **tailored** (P2b — currently exists, 0)
- notes

## JSON Files
- `data/answers.json`: `{question_lower: answer}`
- `data/unanswered.json`: `list[UnansweredQuestion]`
- `data/.control/state.txt`: `idle|running|paused|stopped`
- `data/.control/command.txt`: `pause|resume|stop`
- `data/.control/heartbeat.txt`: ISO timestamp
