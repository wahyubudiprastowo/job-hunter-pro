# PATCH 31.1 — Critical Bug Fixes

Analisa dari log 2026-06-25:

## 🐛 4 Bug Critical

### Bug A: SELECTOR Catching Navbar Bukan Job Cards 🔥 PRIORITY
```
Skipped: <a id="FindJobs" aria-label="Home">
Skipped: <a id="CompanyReviews">  
Skipped: <a id="FindSalaries">
```
**Cause**: Selector `li[data-jk]` atau generic catching navbar `<li>` items.

**Fix**: Scope ke `#mosaic-jobResults` container only.

### Bug B: PAXZC Code untuk Remote Wrong
```
URL: sc=0kf:attr(DSQF7)attr(PAXZC);
```
**Cause**: PAXZC bukan kode valid Indeed 2026 untuk remote.

**Fix**: Remove sc filter untuk remote, gunakan keyword di query.

### Bug C: Title Extraction Gagal
```
SKIP [ @ Infosys]: title missing required keywords  
   ↑ title kosong!
```
**Cause**: Indeed 2026 title nested dalam pattern berbeda.

**Fix**: 5-strategy title extraction.

### Bug D: NotificationCategory.SUMMARY AttributeError
```
AttributeError: type object 'NotificationCategory' has no attribute 'SUMMARY'
```
**Cause**: Typo — Patch 28 defined `DAILY_SUMMARY`, bukan `SUMMARY`.

**Fix**: Rename `SUMMARY` → `DAILY_SUMMARY` di runner.py.

---

## 📦 Files Touched

| File | Action | Lines |
|---|---|---|
| `packages/extractors/indeed_v2_fixes.py` | NEW | ~250 |
| `packages/extractors/indeed.py` | UPDATE | 3 functions |
| `apps/worker/runner.py` | UPDATE | 1 typo fix |

---

## 1. Install Helper

```cmd
copy patch\job-hunter-pro-patch31.1\packages\extractors\indeed_v2_fixes.py packages\extractors\indeed_v2_fixes.py
```

---

## 2. Update `packages/extractors/indeed.py`

### 2a. Add import

Add at top of file:

```python
from packages.extractors.indeed_v2_fixes import (
    INDEED_SELECTORS_V2,
    INDEED_SCOPE_PREFIX,
    build_indeed_url_v2,
    collect_indeed_cards_v2,
    _extract_title_v2,
)
```

### 2b. Replace `_build_search_url`

FIND existing `_build_search_url` function:

```python
def _build_search_url(self, query, filters):
    # OLD CODE (with PAXZC bug)
    ...
```

REPLACE BODY with:

```python
def _build_search_url(self, query, filters):
    """Build Indeed search URL (Patch 31.1 fixed)."""
    return build_indeed_url_v2(self.base_url, query, filters)
```

### 2c. Replace `collect_job_cards`

FIND existing `collect_job_cards`:

```python
def collect_job_cards(self, max_cards=50):
    # OLD CODE (catching navbar items)
    ...
```

REPLACE BODY with:

```python
def collect_job_cards(self, max_cards=50):
    """Collect cards using scoped selectors (Patch 31.1)."""
    from packages.stealth.humanizer import human_sleep
    
    return collect_indeed_cards_v2(
        driver=self.driver,
        max_cards=max_cards,
        scroll_count=self.config.get("scroll_count", 8),
        sleep_func=human_sleep,
    )
```

### 2d. Update title extraction in `open_job_detail` (if exists)

If your code has its own title extraction logic, replace with:

```python
title = card.get("title") or _extract_title_v2(card.get("_element"))
```

---

## 3. Update `apps/worker/runner.py`

Find around line 821 (the run_bot summary section):

```python
# OLD (causing AttributeError):
category=NotificationCategory.SUMMARY if NotificationCategory else None,
```

REPLACE with:

```python
# NEW:
category=NotificationCategory.DAILY_SUMMARY if NotificationCategory else None,
```

Or use grep:
```cmd
findstr /N "NotificationCategory.SUMMARY" apps\worker\runner.py
```

---

## 4. Test

```cmd
python -m py_compile packages/extractors/indeed_v2_fixes.py
python -m py_compile packages/extractors/indeed.py
python -m py_compile apps/worker/runner.py

python run_web.py
```

Start INDEED only.

**Expected log** (success):

```
Indeed search: Cloud Engineer -> https://www.indeed.com/jobs?q=Cloud+Engineer&l=singapore&fromage=7&sort=date&sc=0kf%3Aattr%28DSQF7%29%3B
                                                                                              ↑ NO MORE attr(PAXZC)!

Found 12 Indeed job card nodes (scoped to results).
                              ↑ "scoped to results" = navbar NOT caught
Collected 10 unique Indeed cards.
                  ↑ N > 0 with proper titles
                  
✅ Applied [Cloud Engineer @ Acme]
                ↑ title not empty anymore

🎉 Run done. Counters: {'applied': 5, ...}
↑ NO MORE AttributeError crash
```

---

## 5. Verification Checklist

- [ ] URL: NO `attr(PAXZC)`, only `attr(DSQF7)` for easy_apply
- [ ] Found N nodes — N < 20 (not 100+ navbar pollution)
- [ ] Collected N unique cards — N > 0 mostly
- [ ] SKIP messages show title: `SKIP [Cloud Engineer @ Acme]` (not blank)
- [ ] No AttributeError crash at end of run
- [ ] DB shows Indeed entries

---

## 6. Expected Impact

| Metric | After Patch 31 | After Patch 31.1 |
|---|:---:|:---:|
| URL accuracy | Partial (PAXZC dummy) | ✅ Correct |
| Card collection | 0-2 (navbar pollution) | ✅ 5-15 real cards |
| Title extraction | Empty | ✅ Populated |
| Run completion | Crash with AttributeError | ✅ Clean finish |

---

## 7. Rollback

Revert function bodies di indeed.py + runner.py.

---

## 8. Known Limits

### Indeed Singapore Job Pool Limited
Even with fixes, "Cloud Engineer in Singapore + remote + last week" might have **genuinely few results** (3-15 per query).

Consider:
- Broader location (e.g., "Singapore Or Remote")
- Longer date range (past_month)
- More queries

### Cloudflare Still Active
Patch 31 already added Cloudflare bypass. If Indeed shows zero results constantly even after fix, kemungkinan Cloudflare aktif. Cek manual di browser.
