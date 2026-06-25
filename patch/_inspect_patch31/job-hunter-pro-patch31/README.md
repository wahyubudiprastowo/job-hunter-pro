# 🔧 Patch 31 — Indeed 2026 Fixes

## 🎯 What's This For

Comprehensive fix untuk Indeed extractor (Patch 22) yang failed di production:

```
Log evidence:
"Found 3 Indeed job card nodes" → "Collected 0 unique cards"
URL: "...attr(DSQF7)attr(DSQF7)..." (DUPLICATE)
```

## 🐛 Bugs Fixed

| # | Bug | Cause | Fix |
|:---:|---|---|---|
| 1 | URL duplicate `attr(DSQF7)` | Both `easy_apply` + `remote` push same code | Remote uses separate mechanism |
| 2 | 0 cards collected from N nodes | Indeed 2026 DOM changed | Multi-strategy `data-jk` extraction + JSON fallback |
| 3 | Cloudflare Turnstile not handled | New CF protection on Indeed | Detection + auto-bypass logic |
| 4 | Stealth insufficient | UC alone not enough | UC + JS overrides + headers |

## 📦 Bundle

| File | Lines | Purpose |
|---|---|---|
| `indeed_2026_fixes.py` | ~450 | Helper functions (additive) |
| `INTEGRATION_SNIPPETS.md` | - | Step-by-step patching guide |
| `apply.cmd` | - | Auto-installer |

## 🚀 Cara Pakai

### Step 1: Install (1 menit)
```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch31.zip

cd job-hunter-pro-patch31
apply.cmd
```

### Step 2: Apply Snippets (30 menit)
Follow `INTEGRATION_SNIPPETS.md` step-by-step:
- `indeed.py`: Replace 3 function bodies
- `browser.py`: Enhanced launch options
- Add Cloudflare check di `search()` + `login()`

### Step 3: Test
```cmd
python run_web.py
REM Click INDEED only
REM Watch log for "Collected N > 0"
```

## ✨ Key Features

### 🎯 Multi-Strategy Job ID Extraction
```python
# Strategy 1: data-jk on card itself
# Strategy 2: data-jk on link inside  
# Strategy 3: extract jk= from href regex
# Strategy 4: id attribute pattern
```

### 🛡️ Cloudflare Turnstile Bypass
- Auto-detect Turnstile widget vs interstitial
- Find checkbox iframe + click human-like
- Wait for clearance + retry logic
- Graceful timeout handling

### 🥷 Enhanced Stealth
- `navigator.webdriver = undefined`
- Spoof plugins, languages, permissions
- Realistic User-Agent (Chrome 121)
- Behavior smoothing

### 💾 Embedded JSON Fallback
Indeed embeds job data di `window.mosaic.providerData`. Kalau DOM extraction fail, parse JSON langsung — **gak peduli DOM changes**!

## 📊 Expected Impact

| Metric | Before P31 | After P31 |
|---|:---:|:---:|
| Card collection success | 0% | 60-90% |
| URL accuracy | Broken | Correct |
| Cloudflare handling | None | Auto-bypass |
| Indeed apply rate | 0/day | 5-10/day |
| Recent Apps shows Indeed | Never | Yes |

## 🛡️ Anti-Breakage

- ✅ Helper module ADDITIVE (`indeed_2026_fixes.py`)
- ✅ Original `indeed.py` patched selectively (rollback easy)
- ✅ Backward compatible (works if Cloudflare absent)
- ✅ Embedded JSON fallback resilient to DOM changes
- ✅ No DB schema changes
- ✅ No credential touches

## 🆘 Rollback

Revert function body changes di `indeed.py` + comment imports.

## 🔗 Related

- Patch 22 — Original Indeed Extractor (this patches it)
- Patch 25 — CAPTCHA Solver (complementary untuk hCaptcha cases)

## 🎯 Limitations

### Cloudflare Cannot Always Be Bypassed
Modern Cloudflare Turnstile sometimes requires:
- Residential IP (not datacenter)
- Real browser session (long warmup)
- Behavioral patterns (mouse movement, scroll)

If bypass fails consistently:
1. Try VPN ke residential IP
2. Use 2Captcha provider untuk Turnstile ($3/1000)
3. Reduce scrape velocity (slower = less suspicious)
