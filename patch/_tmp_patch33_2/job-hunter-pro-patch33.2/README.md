# 🔧 Patch 33.2 — Indeed Discovery Mode Critical Fixes

## 🐛 4 Critical Bugs Fixed

### Bug 1: 🔴 Discovery Mode Filter Bypass (CRITICAL)

**Symptom:**
```
Counters: discovered=0, skipped=67
```
Bot di discovery mode tapi 67 jobs masuk ke applications.db sebagai SKIPPED.

**Root cause**: Filter `title_keywords_include` reject jobs BEFORE save_discovered logic.

**Fix**: Edit runner.py to bypass filters when `discovery_mode=True`.

### Bug 2: 🔴 Title Extraction Empty

**Symptom:**
```
SKIP [ @ Westley Resource]: title missing required keywords
     ↑↑ Title kosong!
```

**Fix**: Add 8-strategy title extraction (more fallbacks).

### Bug 3: 🟡 Wrong Region (US jobs for SG search)

**Symptom**: Search location "Singapore" tapi results dari US companies (Westley, SAIC, MissionRT).

**Root cause**: Bot pakai `indeed.com` (US default) bukan `sg.indeed.com`.

**Fix**: Auto-detect region from search location, use regional domain.

### Bug 4: 🟡 Cloudflare Recurring

**Symptom**: CF muncul lagi after ~3 searches, session crash if user close browser.

**Fix**: Throttle 15 sec between searches.

## 📦 Bundle Contents

| File | Purpose |
|---|---|
| `INTEGRATION_SNIPPETS.md` | 4-step manual edit guide |
| `discovery_filter_helper.py` | Helper module for filter decisions |
| `apply.cmd` | Auto-installer |
| `README.md` | This file |

## 🚀 Cara Pakai

### Step 1: Install Helper (1 min)
```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch33.2.zip

cd job-hunter-pro-patch33.2
apply.cmd
```

### Step 2: Apply 4 Manual Fixes

Read `INTEGRATION_SNIPPETS.md` and edit:

1. **`apps/worker/runner.py`** — Bypass filters in discovery mode
2. **`packages/extractors/indeed.py`** — Region auto-detect + throttling
3. **`packages/extractors/indeed_v2_fixes.py`** — Title extraction fallbacks
4. **Restart bot**

Total edit time: ~20 menit

### Step 3: Test

```cmd
python run_web.py
# Click "Scrape Indeed (100)" at /discovered
```

**Expected NEW behavior:**
```
Indeed region: sg -> https://sg.indeed.com   ← Singapore!
Found 25 Indeed job card nodes
Collected 22 unique Indeed cards
Discovered [Cloud Engineer @ Acme Singapore] fit=85   ← Real SG jobs!
Throttle: sleeping 10.5s before next search   ← Anti-CF
...
🎉 Run done. Counters: {'discovered': 22, 'auto_apply_queued': 5, 'skipped': 0}
                                          ↑↑↑↑↑ Going to discovered_jobs!
```

## 📊 Expected Impact

| Metric | Before | After |
|---|:---:|:---:|
| Region used | US (wrong) | SG (correct) |
| Jobs to discovered_jobs | 0 | 80-100 |
| Title extraction | Empty | Populated |
| Cloudflare frequency | Every 3 searches | Once/session |
| US jobs in SG search | 100% | <10% |

## ✅ Anti-Breakage

- ✅ Helper module ADDITIVE
- ✅ Manual edits documented with clear before/after
- ✅ Discovery mode logic still works (gate by flag)
- ✅ Apply mode behavior preserved
- ✅ Queue mode filters still apply

## 🎯 Why This Matters

### Before Fixes:
- 67 wrong-region jobs filtered into wrong DB table
- 0 jobs in /discovered (the whole point!)
- Cloudflare disruption mid-session
- Wasted scrape time

### After Fixes:
- ✅ Real Singapore jobs scraped
- ✅ All go to /discovered for review
- ✅ Auto-rules apply (fit-based)
- ✅ Sustainable scrape rate

## 🔗 Related

- Patch 31.1 — Bug fixes (earlier)
- Patch 32 — Discovery system
- Patch 33 — Glassdoor (extends multi-region pattern)
