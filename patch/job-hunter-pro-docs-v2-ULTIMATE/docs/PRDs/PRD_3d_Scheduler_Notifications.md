# PRD: Phase 3d — Scheduler + Notifications

## 0. Status: ⏭️ PLANNED

## 1. Problem
User wants bot to run on schedule (e.g., 9 AM daily) and notify outcomes via Telegram/Teams/Email.

## 2. Goals
- ✅ Cron-style schedule per platform
- ✅ Notifications hub: Email/Telegram/Teams/Discord/Webhook
- ✅ Granular event subscription (applied / milestone / captcha / error)

## 3. Tech Spec
- `apps/scheduler/` (new)
- `packages/notifications/` (new) — base + 5 channels
- Tech: APScheduler, python-telegram-bot, requests for webhooks
- Config: `scheduler:` + `notifications:` blocks

## 4. Implementation
```yaml
scheduler:
  enabled: true
  schedules:
    - name: "Morning EU"
      cron: "0 9 * * MON-FRI"
      timezone: "Europe/Berlin"

notifications:
  telegram:
    enabled: true
    events: [applied, captcha, error]
  teams:
    webhook_url: ...
    events: [milestone]
```

## 5. Checklist
- [ ] APScheduler integration
- [ ] Per-channel notifier classes
- [ ] Config block
- [ ] UI: schedule editor

## 6. Acceptance
- [ ] Schedule fires on time
- [ ] Notification ≤ 5s after event
- [ ] Multi-channel works
