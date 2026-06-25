# PATCH 33.2 — Indeed Discovery Mode Fixes

Critical fixes dari log analysis 2026-06-25 21:48:52:

## 🐛 4 Issues Fixed

### Issue 1: Discovery Mode Filter Bug (CRITICAL)
```
Counters: discovered=0, skipped=67
```
Bot discovery_mode aktif, tapi 67 jobs masuk ke applications.db as SKIPPED.

**Cause**: Filter `title_keywords_include` reject jobs BEFORE sampai save_discovered.

**Fix**: Bypass strict filters when discovery_mode=True.

### Issue 2: Title Extraction Empty
```
SKIP [ @ Westley Resource]: title missing required keywords
```
Selector gak match, return empty string.

**Fix**: Multi-strategy title fallback.

### Issue 3: Wrong Region (US jobs for SG search)
Bot pakai `indeed.com` dengan `l=singapore` → US-based jobs muncul.

**Fix**: Force `sg.indeed.com` untuk Singapore searches.

### Issue 4: Cloudflare Recurring
Session crash + CF re-trigger after ~3 searches.

**Fix**: Add pause between searches + session retry logic.

---

## 🛠️ Apply Fixes (Manual Edits)

### Fix 1: Edit `apps/worker/runner.py`

FIND filter section dengan title_keywords (sekitar line 680-690):

```python
# OLD code (currently rejecting in discovery mode):
if title_kw_include:
    if not any(kw in job.title.lower() for kw in title_kw_include):
        _record_skip_full(job, SkipReason.TITLE_KEYWORD_MISSING, ...)
        continue
```

REPLACE with:

```python
# NEW: Discovery mode bypass title filter
if title_kw_include and not discovery_mode:
    if not any(kw in job.title.lower() for kw in title_kw_include):
        _record_skip_full(job, SkipReason.TITLE_KEYWORD_MISSING, ...)
        continue
# In discovery mode: skip filter, let user curate in UI
```

Do the same for these filters (add `and not discovery_mode`):
- `title_keywords_exclude`
- `description_keywords_exclude`
- `company_blacklist`
- `min_salary`

### Fix 2: Edit `packages/extractors/indeed.py`

FIND `_resolve_indeed_base_url` function (around line 200):

```python
# OLD:
def _resolve_indeed_base_url(self):
    region = self.config.get("region", "")
    if not region or region == "global":
        logger.warning(f"Unknown Indeed region '{region}' - falling back to https://www.indeed.com")
        return "https://www.indeed.com"
```

REPLACE with location auto-detect:

```python
def _resolve_indeed_base_url(self):
    region = self.config.get("region", "").strip().lower()
    
    # NEW: Auto-detect region from search location
    if not region or region == "auto" or region == "global":
        location = self.config.get("search", {}).get("location", "").lower()
        region_keywords = {
            "sg": ["singapore"],
            "uk": ["london", "uk", "united kingdom"],
            "de": ["germany", "berlin", "munich"],
            "fr": ["paris", "france"],
            "ca": ["canada", "toronto", "vancouver"],
            "au": ["australia", "sydney", "melbourne"],
            "in": ["india", "bangalore", "mumbai"],
            "nl": ["netherlands", "amsterdam"],
        }
        for r, keywords in region_keywords.items():
            if any(kw in location for kw in keywords):
                region = r
                break
        if not region:
            region = "us"  # Default
    
    domain_map = {
        "us": "https://www.indeed.com",
        "sg": "https://sg.indeed.com",
        "uk": "https://uk.indeed.com",
        "de": "https://de.indeed.com",
        "fr": "https://fr.indeed.com",
        "ca": "https://ca.indeed.com",
        "au": "https://au.indeed.com",
        "in": "https://in.indeed.com",
        "nl": "https://nl.indeed.com",
    }
    
    base_url = domain_map.get(region, "https://www.indeed.com")
    logger.info(f"Indeed region: {region} -> {base_url}")
    return base_url
```

### Fix 3: Edit `packages/extractors/indeed_v2_fixes.py`

FIND `_extract_title_v2` function. ADD more fallback strategies:

```python
def _extract_title_v2(node) -> str:
    """Multi-strategy title extraction (FIX: more fallbacks)."""
    strategies = [
        # Strategy 1: span title attribute (most reliable)
        ("h2.jobTitle span[title]", "title"),
        # Strategy 2: link aria-label
        ("h2.jobTitle a", "aria-label"),
        # Strategy 3: link text content
        ("h2.jobTitle a", "text"),
        # NEW Strategy 4: any span inside h2 (deep)
        ("h2.jobTitle span", "text"),
        # NEW Strategy 5: h2 text itself
        ("h2.jobTitle", "text"),
        # NEW Strategy 6: data-testid
        ("[data-testid='job-title']", "text"),
        # NEW Strategy 7: any visible link text
        ("a[data-jk]", "text"),
        # NEW Strategy 8: aria-label on card
        ("[role='group'][aria-label]", "aria-label"),
    ]
    
    for selector, attr in strategies:
        try:
            elem = node.find_element(By.CSS_SELECTOR, selector)
            if attr == "text":
                text = elem.text.strip()
            else:
                text = elem.get_attribute(attr) or ""
            if text and len(text) > 3:  # Reject too-short matches
                return text.strip()
        except NoSuchElementException:
            continue
        except Exception:
            continue
    
    return ""
```

### Fix 4: Throttle searches in indeed.py

FIND `search()` method. ADD pause between searches:

```python
def search(self, filters):
    """Search with throttling to avoid Cloudflare."""
    if not filters.queries:
        return
    
    # NEW: Throttle to avoid Cloudflare re-trigger
    if hasattr(self, "_last_search_time"):
        import time
        elapsed = time.time() - self._last_search_time
        if elapsed < 15:  # Min 15 sec between searches
            sleep_for = 15 - elapsed
            logger.info(f"Throttle: sleeping {sleep_for:.1f}s before next search")
            time.sleep(sleep_for)
    
    q = filters.queries[0]
    url = self._build_search_url(q, filters)
    logger.info(f"Indeed search: {q} -> {url}")
    self.driver.get(url)
    human_sleep(3, 5)
    
    # Track time
    import time
    self._last_search_time = time.time()
    
    # ... rest of existing search code ...
```

---

## ✅ Verification After Fixes

Run discovery scrape again:

```cmd
python run_web.py
# Click "Scrape Indeed (100)" at /discovered
```

Expected log:
```
Indeed region: sg -> https://sg.indeed.com    ← FIXED Region
Indeed search: Cloud Engineer -> https://sg.indeed.com/jobs?...
Found 25 Indeed job card nodes (scoped to results).
Collected 22 unique Indeed cards.
Discovered [Cloud Engineer @ Acme Singapore] fit=85  ← FIXED Title!
Discovered [DevOps Engineer @ Stripe SG] fit=78
Throttle: sleeping 10.5s before next search    ← Anti-Cloudflare
...
```

Check at `/discovered`:
- Real jobs from sg.indeed.com
- Titles populated
- Auto-rules working (fit-based status)
- NO more "blacklisted_title" reasons

## 📊 Expected Impact

| Metric | Before | After |
|---|:---:|:---:|
| Region | indeed.com (US) | sg.indeed.com (Singapore) |
| Jobs to discovered_jobs | 0 | 80-100 |
| Title extraction | Empty | Populated |
| Cloudflare trigger | Every 3 searches | Once per session |
| Wrong-region results | 100% | <10% |