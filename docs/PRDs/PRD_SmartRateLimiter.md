# PRD: Smart Rate Limiter

## 0. Status
| Field | Value |
|---|---|
| Phase | Cross-cutting account safety |
| Status | PRD ready |
| Priority | High |
| Patch | 19 |
| Estimate | 4-6 hours |

## 1. Problem Statement

The project has historical evidence that aggressive repeated apply activity can trigger LinkedIn-side throttling or anti-bot behavior.

Current gaps:

- daily count is not enforced persistently across runs
- there is no first-class rate-limit detection and cooldown mechanism
- safety state is not surfaced clearly in the dashboard

## 2. User Story

As a job-seeker using this bot, I want:

1. daily caps enforced per platform
2. detection of LinkedIn-style rate-limit messages
3. auto-pause/cooldown when a limit is hit
4. safety state preserved across restarts
5. dashboard visibility into current cap usage

## 3. Goals And Non-Goals

### Goals

- track daily apply count per platform and date
- block further apply attempts once cap is reached
- detect rate-limit warning text robustly
- persist cooldown state
- expose status in dashboard

### Non-Goals

- machine learning throttling
- perfect anti-detection guarantees
- multi-platform aggregate strategy optimization in v1

## 4. Acceptance Criteria

1. Daily count is tracked accurately per platform/date.
2. Cap check happens before each apply attempt.
3. If cap is reached, bot skips safely and stops wasting actions.
4. Cooldown state persists across restart.
5. Dashboard can show current cap/cooldown state.

## 5. Technical Spec

### New Module

```text
packages/extractors/rate_limiter.py
```

### Storage

Add a DB table for per-platform daily count and cooldown data.

Possible fields:

- `platform`
- `date`
- `count`
- `blocked_until`
- `last_warning_at`

### Detection

Use a curated list of LinkedIn warning phrases and page/modal content checks.

### Runner Integration

- check daily cap before attempting apply
- increment daily count after success
- if warning detected, persist cooldown and stop current run safely

### Dashboard

Expose:

- `X / daily_cap` applies today
- blocked/cooldown state when active

## 6. Integration Points

- `packages/storage/db.py`
- `apps/worker/runner.py`
- `packages/core/models.py`
- `apps/web/app.py`
- `apps/web/templates/dashboard.html`
- `config.yaml`

## 7. Config Additions

```yaml
global_limits:
  total_apply_per_day: 12
  total_apply_per_run: 8
  adaptive_throttle: true
  cooldown_hours_on_limit: 24
```

Final values should be chosen from actual production use, not copied blindly from old incident notes.

## 8. Testing Strategy

### Unit

- detection text matching
- count increment logic
- cooldown persistence

### Integration

- cap reached on same day across restart
- cooldown survives restart
- dashboard reflects cap state

## 9. Rollout Advice

1. ship with conservative defaults
2. observe for several runs
3. only then tune caps upward if safe

## 10. Related

- [../RATE_LIMIT_RECOVERY.md](../RATE_LIMIT_RECOVERY.md)
- [PRD_2d_Fit_Scoring.md](PRD_2d_Fit_Scoring.md)
- [../NEXT_STEPS_ROADMAP.md](../NEXT_STEPS_ROADMAP.md)
