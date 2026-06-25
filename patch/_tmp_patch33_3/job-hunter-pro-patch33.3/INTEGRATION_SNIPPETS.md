# PATCH 33.3 — Indeed + Glassdoor Production Fixes

## 🎯 Apa Yang Patch Ini Fix

Berdasarkan log production 2026-06-25:

### ✅ Yang Sudah Working
- Indeed: 49 jobs discovered (BCG Platinion fit 78!)
- Discovery flow end-to-end proven
- Cloudflare helper restore URL

### 🐛 Yang Perlu Fix
1. **Indeed**: `element not interactable` (9 jobs failed)
2. **Glassdoor**: Profile setup workflow gak jelas
3. **Both**: Need pre-flight verification

---

## 📦 Files Yang Di-Touch

| File | Action | Lines |
|---|---|---|
| `packages/extractors/robust_click.py` | NEW | ~150 |
| `scripts/check_glassdoor_ready.py` | NEW | ~140 |
| `packages/extractors/indeed.py` | UPDATE | ~5 |

---

## 🛠️ Fix 1: Indeed `element not interactable`

### Problem
```
ERROR: open_job_detail: element not interactable: 
[object HTMLDivElement] has no size and location
```

Cause: Element ada di DOM tapi belum visible/positioned saat di-click.

### Solution: Edit `packages/extractors/indeed.py`

**FIND** function `open_job_detail` (around line 555-565):

```python
# OLD code (line ~561):
ActionChains(d).move_to_element(el).pause(0.2).click().perform()
```

**REPLACE with:**

```python
# NEW: Use robust click with fallback strategies
from packages.extractors.robust_click import robust_click

if not robust_click(d, el, max_retries=4, scroll=True):
    logger.warning(f"All click strategies failed for job card")
    raise ElementNotInteractableException("Robust click exhausted all strategies")
```

### Add Import at Top of `indeed.py`

```python
# ADD at top with other imports:
from packages.extractors.robust_click import robust_click
```

### Expected Result
- 84% → 95%+ success rate on `open_job_detail`
- 9 failed jobs → 1-2 failed jobs (transient network)

---

## 🛠️ Fix 2: Glassdoor Pre-Flight Verification

### Problem
User reset profile → langsung trigger scrape → bot gagal karena Chrome belum stable + profile belum punya session.

### Solution: Mandatory pre-flight check

**Workflow baru:**

```
Step 1: Reset profile (via UI button)
Step 2: Chrome launched dengan profile baru
Step 3: 🛑 USER MUST: Sign in Google + browse 5-10 jobs + close Chrome
Step 4: Run pre-flight check:
        python scripts/check_glassdoor_ready.py
Step 5: HANYA jika 5/5 PASS, baru trigger "Scrape Glassdoor"
```

### Optional Auto-Check in UI

Edit `apps/web/app.py` route `/discovered/trigger`:

**FIND** the trigger handler. **ADD** pre-flight check for Glassdoor:

```python
@app.route("/discovered/trigger", methods=["POST"])
def discovered_trigger():
    platforms_str = request.form.get("platforms", "")
    platforms = [p.strip() for p in platforms_str.split(",") if p.strip()]
    
    # NEW: Pre-flight check for Glassdoor
    if "glassdoor" in platforms:
        from pathlib import Path
        profile_path = Path("./.chrome-profile-glassdoor")
        cookies_file = profile_path / "Default" / "Cookies"
        
        # Check profile size
        if profile_path.exists():
            size_mb = sum(
                f.stat().st_size for f in profile_path.rglob("*") if f.is_file()
            ) / (1024 * 1024)
        else:
            size_mb = 0
        
        if not cookies_file.exists() or size_mb < 50:
            flash(
                "Glassdoor profile not ready. Run prewarm first: "
                "python scripts/prewarm_glassdoor.py"
            )
            return redirect(url_for("discovered"))
    
    # ... rest of existing trigger code ...
```

---

## 🛠️ Fix 3: Indeed Cloudflare Mid-Session

### Problem
After scrape ~5 queries, Cloudflare muncul lagi. User verify manual, bot lanjut. **Annoying but workable.**

### Solution: Adaptive query reduction

**Edit `config.yaml`** untuk Indeed:

```yaml
platforms:
  indeed:
    enabled: true
    max_apply_per_run: 5
    scroll_count: 8
    region: "sg"
    
    search:
      # REDUCED queries (was 10, now 5) to avoid Cloudflare re-trigger
      queries:
        - "Cloud Infrastructure Engineer"
        - "DevOps Engineer"
        - "Platform Engineer"
        - "Site Reliability Engineer"
        - "Senior System Administrator"
      
      location: "Singapore"
      remote: true
      hybrid: true
      date_posted: "past_week"
      easy_apply_only: true
```

**Rationale**: 5 queries × ~10 jobs = 50 jobs. Lebih sustainable + less Cloudflare risk.

---

## 📦 Install Patch

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch33.3.zip

cd job-hunter-pro-patch33.3
apply.cmd
```

Then apply manual edits per `INTEGRATION_SNIPPETS.md`.

---

## ✅ Verification

### Test Indeed Click Fix
```cmd
python -m py_compile packages/extractors/robust_click.py
python -m py_compile packages/extractors/indeed.py

python run_web.py
# Click "Scrape Indeed (100)" at /discovered
```

Expected: < 5 jobs failed (was 9 sebelum fix).

### Test Glassdoor Pre-Flight
```cmd
python scripts\check_glassdoor_ready.py
```

Output should be `5/5 checks passed` BEFORE clicking scrape.

If checks fail:
1. Close all Chrome instances
2. Run `python scripts\prewarm_glassdoor.py`
3. Sign in Google, browse 5-10 jobs
4. Close Chrome
5. Re-run check_glassdoor_ready.py
6. THEN click "Scrape Glassdoor"
