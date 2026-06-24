# PATCH 28 — Integration Snippets

## What This Adds
- Telegram notifications (primary)
- Multi-channel architecture (Email/Teams/Discord ready for future)
- DB-backed notification log
- Stats API for dashboard

## Files Touched

| File | Action | Lines |
|---|---|---|
| `packages/notifications/base.py` | NEW | ~90 |
| `packages/notifications/telegram.py` | NEW | ~120 |
| `packages/notifications/manager.py` | NEW | ~160 |
| `packages/notifications/__init__.py` | NEW | ~20 |
| `apps/worker/runner.py` | UPDATE | +30 |
| `config.yaml` | ADD section | +25 |
| `.env` | ADD credentials | +2 |

## 1. Copy Modules

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
mkdir packages\notifications 2>$null
copy patch\job-hunter-pro-patch28\packages\notifications\*.py packages\notifications\
```

## 2. Telegram Bot Setup (5 minutes)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts (name, username)
4. Copy the TOKEN (e.g., `123456789:ABCDEF...`)
5. Start chat with your new bot, send `/start`
6. Open: `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. Find `chat.id` in response (e.g., `12345678`)
8. Save TOKEN + CHAT_ID

## 3. Add Credentials (`.env`)

```bash
# Telegram Bot Notifications (Patch 28)
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_CHAT_ID=12345678
```

## 4. Add Config (`config.yaml`)

```yaml
# ===== Notifications (Patch 28 - Phase 3d) =====
notifications:
  enabled: true                # Master switch
  
  channels:
    telegram:
      enabled: true
      min_level: "info"        # info | success | warning | error | critical
      categories: []           # Empty = all categories; or list specific ones:
                               # ["bot_state", "apply_success", "rate_limit", "milestone", "daily_summary", "error"]
      parse_mode: "HTML"
      disable_notification: false  # Silent or with sound
    
    # Future channels (uncomment when implemented):
    # email:
    #   enabled: false
    #   smtp_host: "smtp.gmail.com"
    #   ...
    # teams:
    #   enabled: false
    #   webhook_url: ""
```

## 5. Integration in `apps/worker/runner.py`

ADD imports:

```python
try:
    from packages.notifications import (
        NotificationManager,
        NotificationPayload,
        NotificationLevel,
        NotificationCategory,
    )
    from packages.notifications.manager import notify
    _HAS_NOTIF = True
except ImportError:
    NotificationManager = None
    notify = lambda *a, **k: None
    _HAS_NOTIF = False
```

INITIALIZE manager after `store.init_db()`:

```python
# Patch 28: Init NotificationManager
notif_manager = None
if _HAS_NOTIF:
    try:
        notif_manager = NotificationManager.from_config(config)
    except Exception as e:
        logger.warning(f"NotificationManager init failed: {e}")
```

SEND notifications at key events:

### Bot Start
```python
notify(notif_manager, 
    "🚀 Bot Started",
    f"Job-Hunter Pro started in {mode} mode",
    level=NotificationLevel.INFO,
    category=NotificationCategory.BOT_STATE,
    metadata={"mode": mode, "platforms": list(extractors_dict.keys())}
)
```

### Apply Success
```python
if result.status == ApplyStatus.APPLIED:
    counters["applied"] += 1
    notify(notif_manager,
        f"✅ Applied: {job.title}",
        f"Successfully applied to {job.company} ({platform_name})",
        level=NotificationLevel.SUCCESS,
        category=NotificationCategory.APPLY_SUCCESS,
        metadata={
            "company": job.company,
            "title": job.title,
            "platform": platform_name,
            "fit_score": fit_result.score if fit_result else None,
            "total_today": counters["applied"],
        }
    )
```

### Milestone (every 10 applies)
```python
if counters["applied"] % 10 == 0 and counters["applied"] > 0:
    notify(notif_manager,
        f"🎉 Milestone: {counters['applied']} applies!",
        f"Bot has reached {counters['applied']} applications today.",
        level=NotificationLevel.SUCCESS,
        category=NotificationCategory.MILESTONE,
    )
```

### Rate Limit Detected (with Patch 19)
```python
if rate_limit_detected:
    notify(notif_manager,
        "🛑 Rate Limit Hit",
        f"LinkedIn rate limit detected. Bot pausing 24h.",
        level=NotificationLevel.ERROR,
        category=NotificationCategory.RATE_LIMIT,
        metadata={"platform": "linkedin", "cooldown_hours": 24}
    )
```

### Bot Stopped
```python
notify(notif_manager,
    "⏹ Bot Stopped",
    f"Bot stopped. Final: {counters['applied']} applied, {counters['failed']} failed.",
    level=NotificationLevel.INFO,
    category=NotificationCategory.BOT_STATE,
    metadata=counters,
)
```

### Crash/Error
```python
except Exception as e:
    logger.exception("Run crashed")
    notify(notif_manager,
        "🚨 Bot Crashed",
        f"Bot crashed: {str(e)[:200]}",
        level=NotificationLevel.CRITICAL,
        category=NotificationCategory.ERROR,
        metadata={"exception": str(e), "type": type(e).__name__}
    )
```

## 6. Add Test Button to UI (Optional)

In `apps/web/app.py`:

```python
@app.route("/control/notif-test", methods=["POST"])
def control_notif_test():
    try:
        import yaml
        cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
        from packages.notifications import NotificationManager
        manager = NotificationManager.from_config(cfg)
        results = manager.test_all()
        msgs = []
        for ch, (ok, msg) in results.items():
            emoji = "✅" if ok else "❌"
            msgs.append(f"{emoji} {ch}: {msg}")
        flash(" | ".join(msgs) if msgs else "No channels enabled")
    except Exception as e:
        flash(f"Test failed: {e}")
    return redirect(url_for("dashboard"))
```

In `dashboard.html`, add button next to "Test AI":

```html
<form method="post" action="/control/notif-test" style="display:inline">
  <button class="btn btn-outline-primary btn-sm">
    <i class="bi bi-bell"></i> Test Notifications
  </button>
</form>
```

## 7. Verification

```powershell
# Syntax check
python -m py_compile packages/notifications/base.py packages/notifications/telegram.py packages/notifications/manager.py

# Manual test
python -c "
import os
os.environ['TELEGRAM_BOT_TOKEN'] = 'YOUR_TOKEN'
os.environ['TELEGRAM_CHAT_ID'] = 'YOUR_CHAT_ID'

from packages.notifications.telegram import TelegramChannel
from packages.notifications.base import NotificationPayload, NotificationLevel

ch = TelegramChannel({'enabled': True})
result = ch.send(NotificationPayload(
    title='Test from Patch 28',
    message='If you see this, Telegram works!',
    level=NotificationLevel.SUCCESS,
))
print(f'Success: {result.success}')
print(f'Error: {result.error}')
"
```

If you see message in your Telegram, integration works.

## 8. Recommended Categories Subscription

For different use cases:

**Minimal (only critical):**
```yaml
telegram:
  categories: ["error", "rate_limit"]
  min_level: "error"
```

**Daily user (mid info):**
```yaml
telegram:
  categories: ["milestone", "rate_limit", "daily_summary", "error"]
  min_level: "warning"
```

**Power user (everything):**
```yaml
telegram:
  categories: []  # All
  min_level: "info"
```

## 9. Anti-Breakage Compliance

- ✅ ADDITIVE package (new `packages/notifications/`)
- ✅ Backward compatible (notifications.enabled: false = no behavior change)
- ✅ Optional dependency (try/except for missing module)
- ✅ Graceful degradation (channel failure doesn't crash bot)
- ✅ DB-backed log (separate table, no schema breaking)
- ✅ Per-channel min_level + category filtering
- ✅ Telegram uses safe HTML escaping
- ✅ All tokens via env (no hardcoding)

## 10. Rollback

```yaml
notifications:
  enabled: false
```

Bot continues without notifications.
