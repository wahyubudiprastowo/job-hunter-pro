# PATCH 33 — Glassdoor Extractor Integration

## 🎯 Decisions Applied (per user)
- ✅ Login: **Both** Email/Password AND Google OAuth (auto-detect)
- ✅ Region: **Auto-detect** via location keyword
- ✅ Apply: **Easy Apply only**
- ✅ Salary: **Use for fit scoring boost**

---

## 📦 Files

| File | Action |
|---|---|
| `packages/extractors/glassdoor.py` | NEW (~700 lines) |
| `scripts/prewarm_glassdoor.py` | NEW |
| `apps/worker/runner.py` | UPDATE (register extractor) |
| `packages/stealth/profile_manager.py` | UPDATE (add glassdoor) |
| `config.yaml` | ADD platforms.glassdoor section |
| `.env` | ADD GLASSDOOR_EMAIL, GLASSDOOR_PASSWORD |

---

## 1. Copy Files

```cmd
copy patch\job-hunter-pro-patch33\packages\extractors\glassdoor.py packages\extractors\
copy patch\job-hunter-pro-patch33\scripts\prewarm_glassdoor.py scripts\
```

## 2. Add Config

ADD to `config.yaml`:

```yaml
# ===== Glassdoor Platform (Patch 33) =====
platforms:
  glassdoor:
    enabled: false              # Start disabled, enable after prewarm
    max_apply_per_run: 5
    scroll_count: 8
    region: "auto"              # auto | us | uk | ca | de | fr | sg | in | au | nl | ie
    login_method: "auto"        # auto | email | google
    
    search:
      queries:
        - "Cloud Infrastructure Engineer"
        - "Azure Cloud Engineer"
        - "DevOps Engineer"
        - "Platform Engineer"
        - "Site Reliability Engineer"
      location: "Singapore"     # Will auto-detect to glassdoor.sg
      remote: true
      date_posted: "past_week"
      easy_apply_only: true
```

## 3. Add Credentials (`.env`)

```bash
# Glassdoor Credentials (Patch 33)
GLASSDOOR_EMAIL=your-email@gmail.com
GLASSDOOR_PASSWORD=your-password

# Note: If using Google OAuth, login Google in profile first
# Bot will detect Google session and skip password entry
```

## 4. Register in `apps/worker/runner.py`

ADD import:

```python
try:
    from packages.extractors.glassdoor import GlassdoorExtractor
    _HAS_GLASSDOOR = True
except ImportError:
    GlassdoorExtractor = None
    _HAS_GLASSDOOR = False
```

ADD to extractor registry:

```python
EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
    "indeed": IndeedExtractor,
    "glassdoor": GlassdoorExtractor if _HAS_GLASSDOOR else None,
}
# Filter out None values
EXTRACTOR_REGISTRY = {k: v for k, v in EXTRACTOR_REGISTRY.items() if v is not None}
```

## 5. Update `profile_manager.py`

Find:
```python
def list_all_profiles() -> list:
    return [get_profile_info(p) for p in ["linkedin", "indeed"]]
```

REPLACE with:
```python
def list_all_profiles() -> list:
    return [get_profile_info(p) for p in ["linkedin", "indeed", "glassdoor"]]
```

Same for `cleanup_old_backups`:
```python
for platform in ["linkedin", "indeed", "glassdoor"]:
```

## 6. Setup Glassdoor (REQUIRED!)

### Step A: Pre-warm Profile
```cmd
python scripts\prewarm_glassdoor.py
```

Browser opens. Lakukan:
1. ✅ Complete Cloudflare (if shown)
2. ✅ Sign in to Glassdoor:
   - **Easy way**: Click "Sign in with Google" → uses Chrome profile
   - **OR**: Enter email + password manually
3. ✅ Complete profile (CV upload optional but recommended)
4. ✅ Browse 5-10 jobs (humanize)
5. ✅ Close browser

### Step B: Test in Bot

Edit config.yaml:
```yaml
platforms:
  glassdoor:
    enabled: true
```

Run bot:
```cmd
python run_web.py
```

Visit `/discovered`:
- Click "Scrape Glassdoor" button (if Patch 32.2 integrated)
- OR click "Start All Platforms" with discovery enabled

## 7. Salary Boost in Fit Scoring (Optional Bonus)

The Glassdoor extractor parses salary into:
```python
job.raw["salary_parsed"] = {
    "min": 120000,
    "max": 150000,
    "currency": "USD",
    "period": "year",
}
```

To use for fit_score boost, update fit scorer (Patch 17):

```python
# In your scorer.py:
def calculate_fit_with_salary_boost(ai_provider, cv_text, job):
    base_score = calculate_fit_score(ai_provider, cv_text, job)
    
    salary = job.raw.get("salary_parsed", {})
    if salary.get("max"):
        # Calculate annual USD
        from packages.extractors.glassdoor import salary_to_annual_usd
        annual_usd = salary_to_annual_usd(salary)
        
        # Boost +5 for high salary (>$120k), +10 for very high (>$180k)
        if annual_usd and annual_usd > 180000:
            base_score.score = min(100, base_score.score + 10)
            base_score.reasoning += " | +10 high salary boost"
        elif annual_usd and annual_usd > 120000:
            base_score.score = min(100, base_score.score + 5)
            base_score.reasoning += " | +5 good salary boost"
    
    return base_score
```

## 8. Discovery Buttons Update (if Patch 32.2 integrated)

Update `discovered.html` to add Glassdoor button:

```html
<form method="post" action="/discovered/trigger" style="display: inline;">
  <input type="hidden" name="platforms" value="glassdoor">
  <input type="hidden" name="max_per_session" value="100">
  <input type="hidden" name="scroll_depth" value="15">
  <button type="submit" class="btn btn-warning btn-sm">
    <i class="bi bi-star"></i>
    Scrape Glassdoor (100)
  </button>
</form>

<!-- Update "Both" button to "All" -->
<form method="post" action="/discovered/trigger" style="display: inline;">
  <input type="hidden" name="platforms" value="linkedin,indeed,glassdoor">
  <input type="hidden" name="max_per_session" value="100">
  <button type="submit" class="btn btn-success btn-sm">
    <i class="bi bi-globe2"></i>
    Scrape All Platforms (300)
  </button>
</form>
```

## 9. Test

```cmd
python -m py_compile packages/extractors/glassdoor.py
python -m py_compile scripts/prewarm_glassdoor.py

python run_web.py
```

Expected log when bot starts Glassdoor:
```
Glassdoor region: sg -> https://www.glassdoor.sg
AI question fallback enabled for Glassdoor.
Launching Chrome (profile=./.chrome-profile-glassdoor)
Already logged in to Glassdoor.
Glassdoor search: Cloud Engineer -> https://www.glassdoor.sg/Job/jobs.htm?...
Found 30 Glassdoor job card nodes.
Collected 28 unique Glassdoor cards.
```

## 10. Anti-Breakage

- ✅ Helper module ADDITIVE
- ✅ Backward compatible (existing extractors untouched)
- ✅ Optional dependency (try/except imports)
- ✅ Region auto-detect with safe fallback
- ✅ Multi-strategy job_id extraction
- ✅ Cloudflare integration (Patch 31.2)
- ✅ Profile management (Patch 32.3)
- ✅ AI question fallback (Patch 3)
- ✅ Fit scoring + salary boost (Patch 17)

## 11. Known Limitations

### Cloudflare
Glassdoor uses Cloudflare like Indeed. **Pre-warm script is essential** for first-time setup.

### Google OAuth
Requires Chrome profile to have Google session. Bot can't auto-login Google itself.

### Region Detection
Falls back to US (`glassdoor.com`) if location doesn't match keywords. Override with `region: "sg"` (etc.) in config.

### Easy Apply Availability
Not all Glassdoor jobs have Easy Apply. External jobs marked as `EXTERNAL` status.

## 12. Rollback

Remove `glassdoor.py` + `prewarm_glassdoor.py` + config section. No DB changes.
