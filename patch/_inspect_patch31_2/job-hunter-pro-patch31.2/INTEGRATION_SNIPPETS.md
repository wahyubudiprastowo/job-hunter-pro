# PATCH 31.2 — Integration Snippets

## 🎯 What This Does

1. **Pre-warm script** (`scripts/prewarm_indeed.py`) — User runs once to setup CF clearance
2. **Better detection** (`cloudflare_helper.py`) — URL-based, no false positives  
3. **Longer wait** (5 min instead of 60s)
4. **Hard block detection** — Stop early if Ray ID blocked

---

## 1. Install Files

```cmd
copy patch\job-hunter-pro-patch31.2\packages\extractors\cloudflare_helper.py packages\extractors\
mkdir scripts 2>nul
copy patch\job-hunter-pro-patch31.2\scripts\prewarm_indeed.py scripts\
```

## 2. Update `packages/extractors/indeed.py`

### 2a. Add import

```python
from packages.extractors.cloudflare_helper import (
    detect_cloudflare_state,
    handle_cloudflare_safely,
    wait_for_manual_cloudflare_v2,
)
```

### 2b. Replace Cloudflare calls in `login()`

FIND existing calls like:
```python
handle_cloudflare_if_present(d, timeout=60)
```

REPLACE with:
```python
if not handle_cloudflare_safely(d, timeout=300):  # 5 minutes
    logger.warning("=" * 60)
    logger.warning("⚠️  Cloudflare blocked Indeed")
    logger.warning("→ Run pre-warm script:")
    logger.warning("    python scripts/prewarm_indeed.py")
    logger.warning("→ Complete CF manually, close browser")
    logger.warning("→ Re-run bot — should skip CF now")
    logger.warning("=" * 60)
    raise LoginError("Cloudflare blocked - run prewarm")
```

### 2c. Replace in `search()` method

Same pattern — replace `handle_cloudflare_if_present` with `handle_cloudflare_safely`.

## 3. First Time Setup (CRITICAL)

```cmd
# STOP bot first (Ctrl+C in terminal)

# Then run pre-warm:
python scripts\prewarm_indeed.py
```

Browser opens. Complete:
- ✅ Click "Verify you are human"
- ✅ Wait for page transition (~5-10 sec)
- ✅ Sign in to Indeed
- ✅ Browse 5-10 jobs (humanize)
- ✅ Close browser

Cookies saved to `.chrome-profile-indeed/`.

## 4. Test

```cmd
python run_web.py
# Click INDEED only
# Should now skip Cloudflare!
```

## 5. Recurring Maintenance

Cookies expire ~30 days. Re-run prewarm kalau bot fail Cloudflare lagi:

```cmd
python scripts\prewarm_indeed.py
```

Set Windows Task Scheduler kalau mau auto-monthly.

## 6. Anti-Breakage

- ✅ Helper module ADDITIVE
- ✅ Prewarm script SEPARATE (gak modify bot)
- ✅ Replacements in indeed.py optional (use old code as fallback)
- ✅ Backward compatible

## 7. Rollback

Revert indeed.py changes + delete helper + prewarm files.

## 8. Why This Works

Cloudflare tracks:
- Browser fingerprint (UC partially fixes)
- IP reputation (you can't fix this easily)
- Cookies + session history (THIS IS KEY)

When you manually complete CF:
- Cookies set: `cf_clearance` (~30 days)
- Browser fingerprint marked as "human"
- Subsequent visits skip CF check

Bot reuses profile → reuses cookies → CF thinks "this human already verified".

## 9. When Pre-Warm Won't Help

- Indeed detects pattern: many fast searches → re-triggers CF
- Mitigation: 
  - Wider intervals between searches (already in stealth config)
  - Less queries per session
  - Use Indeed less aggressively

## 10. Alternative If Still Failing

| Solution | Cost | Success Rate |
|---|:---:|:---:|
| Pre-warm + cookies (this patch) | Free | 60-80% |
| VPN to Singapore residential | $5-10/mo | 85-95% |
| 2Captcha Turnstile API | $3/1000 | 70-90% |
| FlareSolverr proxy | Free self-host | 80-95% |
| Skip Indeed, LinkedIn only | Free | 100% |

**Honest recommendation**: Try this patch first. If fails consistently, **just focus LinkedIn**. Indeed isn't worth 1 hour of fighting Cloudflare daily.
