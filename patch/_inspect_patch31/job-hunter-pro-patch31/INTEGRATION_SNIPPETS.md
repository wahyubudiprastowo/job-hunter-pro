# PATCH 31 — Indeed 2026 Fixes Integration

## 🐛 Issues Yang Di-Fix

Dari log analysis 2026-06-24:

### Bug #1: URL Duplicate `attr(DSQF7)`
```
BEFORE: sc=0kf%3Aattr%28DSQF7%29attr%28DSQF7%29%3B  (DUPLICATE)
AFTER:  sc=0kf%3Aattr%28DSQF7%29%3B                  (CORRECT)
```

### Bug #2: Found N cards, Collected 0
```
BEFORE: Found 3 Indeed job card nodes. → Collected 0 unique Indeed cards.
AFTER:  Found 3 Indeed job card nodes. → Collected 3 unique Indeed cards.
```

### Bug #3: Cloudflare Turnstile Not Detected
Indeed sekarang pakai Cloudflare Bot Management. Need detection + bypass.

### Bug #4: Stealth Insufficient  
Enhanced anti-detection (navigator.webdriver, plugins, languages spoofing).

---

## 📦 Files

| File | Type | Purpose |
|---|---|---|
| `packages/extractors/indeed_2026_fixes.py` | NEW | Helper module dengan semua fixes |
| `packages/extractors/indeed.py` | UPDATE | Apply patches dari helper |
| `packages/stealth/browser.py` | UPDATE | Enhanced launch options |

---

## 1. Copy Helper Module

```cmd
copy patch\job-hunter-pro-patch31\packages\extractors\indeed_2026_fixes.py packages\extractors\indeed_2026_fixes.py
```

---

## 2. Update `packages/extractors/indeed.py`

### 2a. Add imports at top:

```python
from packages.extractors.indeed_2026_fixes import (
    INDEED_SELECTORS_2026,
    build_search_url_2026,
    collect_job_cards_2026,
    detect_cloudflare_challenge,
    handle_cloudflare_if_present,
    apply_stealth_javascript,
)
```

### 2b. Fix `_build_search_url()` — Replace function body:

FIND existing `_build_search_url` and REPLACE with:

```python
def _build_search_url(self, query, f):
    """Build Indeed search URL with 2026 parameters."""
    return build_search_url_2026(self.base_url, query, f)
```

### 2c. Fix `collect_job_cards()` — Replace function body:

FIND existing `collect_job_cards` and REPLACE with:

```python
def collect_job_cards(self, max_cards=50):
    """2026 multi-strategy collector with embedded JSON fallback."""
    # Check Cloudflare first
    if not handle_cloudflare_if_present(self.driver, timeout=30):
        logger.warning("Could not bypass Cloudflare — proceeding anyway")
    
    from packages.stealth.humanizer import human_sleep
    
    return collect_job_cards_2026(
        driver=self.driver,
        selectors=INDEED_SELECTORS_2026,
        max_cards=max_cards,
        scroll_count=self.config.get("scroll_count", 8),
        sleep_func=human_sleep,
    )
```

### 2d. Update `SELECTORS` dict:

FIND existing `SELECTORS = {...}` and APPEND/REPLACE entries:

```python
# At the top of the file, add:
from packages.extractors.indeed_2026_fixes import INDEED_SELECTORS_2026

# In your existing SELECTORS dict, OVERRIDE these keys:
SELECTORS = {
    # ... your existing entries ...
    
    # OVERRIDE with 2026 selectors:
    "job_card": INDEED_SELECTORS_2026["job_card"],
    "job_card_link": INDEED_SELECTORS_2026["job_card_link"],
    "job_card_title": INDEED_SELECTORS_2026["job_card_title"],
    "job_card_company": INDEED_SELECTORS_2026["job_card_company"],
    "job_card_location": INDEED_SELECTORS_2026["job_card_location"],
}
```

### 2e. Update `search()` method — add Cloudflare check after navigation:

FIND existing `search(self, filters)` function. ADD this AFTER `self.driver.get(url)`:

```python
def search(self, filters):
    if not filters.queries:
        return
    q = filters.queries[0]
    url = self._build_search_url(q, filters)
    logger.info(f"Indeed search: {q} -> {url}")
    self.driver.get(url)
    human_sleep(3, 5)
    
    # NEW: Handle Cloudflare challenge if present
    if not handle_cloudflare_if_present(self.driver, timeout=45):
        logger.warning("Cloudflare challenge could not be bypassed for this search")
        # Continue anyway - maybe partial content available
    
    # Dismiss popup
    try:
        close_btn = self.driver.find_element(
            By.XPATH, "//button[@aria-label='close' or @aria-label='Close']"
        )
        close_btn.click()
        human_sleep(1, 2)
    except NoSuchElementException:
        pass
```

### 2f. Update `login()` method — add stealth + Cloudflare check:

FIND existing `login()` method. ADD at start:

```python
def login(self, email, password, totp_secret=""):
    # NEW: Apply enhanced stealth before any navigation
    try:
        apply_stealth_javascript(self.driver)
    except Exception as e:
        logger.debug(f"Stealth JS apply failed: {e}")
    
    d = self.driver
    d.get(f"{self.base_url}/account/login")
    human_sleep(2, 4)
    
    # NEW: Handle Cloudflare challenge
    handle_cloudflare_if_present(d, timeout=60)
    
    # ... rest of existing login logic ...
```

---

## 3. Update `packages/stealth/browser.py`

ENHANCE Chrome launch options:

```python
from packages.extractors.indeed_2026_fixes import get_stealth_chrome_options

def build_driver(headless=False, user_data_dir="", chrome_profile_dir="Default"):
    import undetected_chromedriver as uc
    
    options = uc.ChromeOptions()
    
    # NEW: Apply stealth options
    for opt in get_stealth_chrome_options():
        options.add_argument(opt)
    
    if headless:
        options.add_argument("--headless=new")
    
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--profile-directory={chrome_profile_dir}")
    
    logger.info(f"Launching Chrome (headless={headless}, profile={user_data_dir}, profile_dir={chrome_profile_dir})")
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    # NEW: Set realistic User-Agent
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })
    
    return driver
```

---

## 4. Test

```cmd
python -m py_compile packages/extractors/indeed_2026_fixes.py
python -m py_compile packages/extractors/indeed.py
python -m py_compile packages/stealth/browser.py

python run_web.py
```

Click Start INDEED only.

Watch log untuk:
```
✅ Stealth JS overrides applied
🛡️  Attempting Cloudflare Turnstile bypass...
🖱️  Turnstile checkbox clicked
✅ Cloudflare cleared
Indeed search: Cloud Engineer -> https://www.indeed.com/jobs?q=Cloud...
Found 15 Indeed job card nodes (2026 selectors).
Collected 12 unique Indeed cards.
```

Kalau muncul `Collected N > 0` cards — BUG #2 fixed!

---

## 5. Verification Checklist

After integration, monitor:

- [ ] URL log gak ada `attr(DSQF7)attr(DSQF7)` duplicate
- [ ] `Collected N` dengan N > 0 (Bug #2 fixed)
- [ ] Indeed apply success → muncul di Recent Applications dengan platform=indeed
- [ ] Rate limiter counter increment per apply
- [ ] DB query: `SELECT platform, COUNT(*) FROM applications GROUP BY platform` shows Indeed > 0

---

## 6. Troubleshooting

### "Still 0 cards collected"

Bisa jadi Cloudflare blocking. Try:

```python
# Set in config.yaml:
platforms:
  indeed:
    region: "us"  # Or specific country
```

### "Cloudflare bypass timeout"

Indeed Cloudflare detection terlalu strict. Options:
- A) Use VPN/proxy ke residential IP
- B) Increase timeout: `handle_cloudflare_if_present(d, timeout=120)`
- C) Use 2Captcha provider (Patch 25) untuk Turnstile

### "Indeed apply iframe not found"

Update `SELECTORS["ia_iframe"]` dengan latest Indeed Apply iframe pattern. Inspect Indeed Apply modal manual.

---

## 7. Rollback

Comment out helper imports + revert function bodies. No DB changes.

---

## 8. Expected Impact

| Metric | Before P31 | After P31 |
|---|:---:|:---:|
| URL accuracy | Broken (duplicate attr) | Correct |
| Card collection | 0% success | 60-90% success |
| Cloudflare handling | None (timeout) | Auto-bypass attempts |
| Stealth | Basic UC | UC + JS overrides + headers |
| Indeed apply rate | 0/day | 5-10/day (typical) |
