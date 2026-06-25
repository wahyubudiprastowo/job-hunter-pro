# PATCH 32 — Discovery & Curation Mode Integration

## 🎯 Decisions Applied (per user)
- ✅ **Scrape Depth**: 50-100 jobs per session
- ✅ **Selection**: Checkbox + bulk actions
- ✅ **Apply Trigger**: Both immediate + scheduled
- ✅ **Browser**: 1 Chrome alternating (Phase 1)
- ✅ **Database**: Separate `discovered_jobs` table

---

## 📦 Files

| File | Type | Purpose |
|---|---|---|
| `packages/storage/discovered_jobs.py` | NEW | DB CRUD for discovered_jobs table |
| `apps/web/templates/discovered.html` | NEW | Review UI with filters + bulk actions |
| `apps/web/app.py` | UPDATE | Add 5 new routes |
| `apps/worker/runner.py` | UPDATE | Add discovery_mode branch |
| `config.yaml` | ADD section | discovery config |

---

## 1. Copy Files

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
copy patch\job-hunter-pro-patch32\packages\storage\discovered_jobs.py packages\storage\
copy patch\job-hunter-pro-patch32\apps\web\templates\discovered.html apps\web\templates\
```

## 2. Add Config

Add to `config.yaml`:

```yaml
# ===== Discovery Mode (Patch 32) =====
discovery:
  enabled: false                # Set true to enable scrape-only mode
  max_per_session: 100          # Cap jobs per discovery run
  scroll_depth: 15              # Deeper scroll than apply mode
  
  # Auto-rules (optional)
  auto_apply_threshold: 90      # Fit >= 90: auto queue for apply
  auto_skip_threshold: 30       # Fit < 30: auto skip
  
  cleanup_after_days: 30        # Delete old discovered jobs after N days
```

## 3. Update `apps/worker/runner.py`

### 3a. Add imports

```python
from packages.storage.discovered_jobs import (
    init_schema as init_discovered_schema,
    save_discovered, list_discovered, update_status,
    STATUS_SELECTED, STATUS_AUTO_APPLY, STATUS_DISCOVERED,
    STATUS_APPLIED, STATUS_FAILED,
)
```

### 3b. Init schema at startup

After `store.init_db()`:

```python
init_discovered_schema()
```

### 3c. Add discovery_mode branch

In `run_bot()`, BEFORE the main extractor loop, add:

```python
discovery_cfg = config.get("discovery", {})
discovery_mode = discovery_cfg.get("enabled", False)

if discovery_mode:
    logger.info("🔍 DISCOVERY MODE — scraping only, no apply")
```

### 3d. Modify per-job logic

In the per-card loop, ADD AT TOP:

```python
# Patch 32: Discovery mode branches
if discovery_mode:
    # Just scrape + save, NO apply
    try:
        job = extractor.open_job_detail(card)
        
        # Run fit scoring if enabled
        fit_score = None
        fit_reasoning = ""
        if fit_scorer:
            try:
                fit_result = fit_scorer.score_job(job)
                fit_score = fit_result.score
                fit_reasoning = fit_result.reasoning
            except Exception as e:
                logger.debug(f"Fit scoring failed: {e}")
        
        # Save to discovered_jobs
        discovered_id = save_discovered({
            "platform": platform_name,
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "description": job.description,
            "salary": job.salary,
            "fit_score": fit_score,
            "fit_reasoning": fit_reasoning,
            "is_easy_apply": job.is_easy_apply,
        })
        
        if discovered_id:
            counters["discovered"] = counters.get("discovered", 0) + 1
            logger.info(f"🔍 Discovered: {job.title} @ {job.company} (fit: {fit_score or '—'})")
            
            # Auto-apply threshold check
            auto_threshold = discovery_cfg.get("auto_apply_threshold", 100)
            auto_skip_threshold = discovery_cfg.get("auto_skip_threshold", 0)
            
            if fit_score is not None:
                if fit_score >= auto_threshold:
                    update_status([discovered_id], STATUS_AUTO_APPLY)
                    counters["auto_apply_queued"] = counters.get("auto_apply_queued", 0) + 1
                elif fit_score < auto_skip_threshold:
                    update_status([discovered_id], "skipped")
                    counters["auto_skipped"] = counters.get("auto_skipped", 0) + 1
        else:
            logger.debug(f"Duplicate: {job.title}")
        
        # Cap check
        if counters.get("discovered", 0) >= discovery_cfg.get("max_per_session", 100):
            logger.info(f"📋 Discovery cap reached ({counters['discovered']})")
            return
        
        continue  # Skip apply logic
    except Exception as e:
        logger.exception(f"Discovery error: {e}")
        continue
```

## 4. Update `apps/web/app.py`

### 4a. Add imports

```python
from packages.storage.discovered_jobs import (
    list_discovered, update_status, get_stats, get_by_ids,
    STATUS_DISCOVERED, STATUS_SELECTED, STATUS_AUTO_APPLY,
    STATUS_SKIPPED, STATUS_SAVED, STATUS_APPLIED,
)
```

### 4b. Add 5 routes

```python
@app.route("/discovered")
def discovered_page():
    """Review discovered jobs."""
    status = request.args.get("status") or None
    platform = request.args.get("platform") or None
    min_fit = request.args.get("min_fit")
    min_fit_int = int(min_fit) if min_fit and min_fit.isdigit() else None
    days = request.args.get("days")
    days_int = int(days) if days and days.isdigit() else None
    
    jobs = list_discovered(
        status=status, platform=platform,
        min_fit=min_fit_int, days=days_int,
        limit=500
    )
    stats = get_stats()
    
    return render_template(
        "discovered.html",
        jobs=jobs,
        stats=stats,
        total=stats.get("total", 0),
        current_status=status,
    )


@app.route("/discovered/action/<int:job_id>", methods=["POST"])
def discovered_action(job_id):
    """Per-job action (selected/saved/skipped)."""
    action = request.form.get("action", "")
    if action in [STATUS_SELECTED, STATUS_AUTO_APPLY, STATUS_SAVED,
                  STATUS_SKIPPED, STATUS_DISCOVERED]:
        count = update_status([job_id], action)
        if count:
            flash(f"✅ Marked as {action}")
        else:
            flash(f"❌ Update failed")
    return redirect(url_for("discovered_page"))


@app.route("/discovered/bulk-action", methods=["POST"])
def discovered_bulk_action():
    """Bulk action on multiple jobs."""
    job_ids_str = request.form.get("job_ids", "")
    action = request.form.get("action", "")
    
    try:
        job_ids = [int(x) for x in job_ids_str.split(",") if x.strip().isdigit()]
    except Exception:
        flash("Invalid selection")
        return redirect(url_for("discovered_page"))
    
    if not job_ids:
        flash("No jobs selected")
        return redirect(url_for("discovered_page"))
    
    if action in [STATUS_SELECTED, STATUS_AUTO_APPLY, STATUS_SAVED,
                  STATUS_SKIPPED, STATUS_DISCOVERED]:
        count = update_status(job_ids, action)
        flash(f"✅ {count} jobs marked as {action}")
    else:
        flash("Invalid action")
    
    return redirect(url_for("discovered_page"))


@app.route("/discovered/apply-selected", methods=["POST"])
def discovered_apply_selected():
    """Trigger apply for all jobs marked 'selected'."""
    selected_jobs = list_discovered(status=STATUS_SELECTED, limit=100)
    
    if not selected_jobs:
        flash("No jobs marked for apply")
        return redirect(url_for("discovered_page"))
    
    # Set session override + start bot
    from apps.worker.control_platforms import set_session_platforms
    
    # Build list of (platform, job_id) for runner to consume
    apply_queue_path = Path("data/.control/apply_queue.json")
    apply_queue_path.parent.mkdir(parents=True, exist_ok=True)
    apply_queue_path.write_text(json.dumps([
        {"platform": j["platform"], "job_id": j["job_id"], 
         "discovered_id": j["id"]}
        for j in selected_jobs
    ]), encoding="utf-8")
    
    # Mark as queued
    update_status([j["id"] for j in selected_jobs], "auto_apply")
    
    # Start bot in apply mode
    global _runner_thread
    diag = controller.get_diagnostics()
    if diag["state"] != "running":
        controller.reset()
        _runner_thread = threading.Thread(target=run_bot, daemon=True)
        _runner_thread.start()
    
    flash(f"🚀 Bot started — applying to {len(selected_jobs)} jobs")
    return redirect(url_for("dashboard"))


@app.route("/discovered/schedule", methods=["POST"])
def discovered_schedule():
    """Schedule apply for later."""
    job_ids_str = request.form.get("job_ids", "")
    schedule_time = request.form.get("schedule_time", "")
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(schedule_time)
        scheduled_ts = int(dt.timestamp())
        
        job_ids = [int(x) for x in job_ids_str.split(",") if x.strip().isdigit()]
        
        if job_ids:
            update_status(job_ids, STATUS_AUTO_APPLY, scheduled_at=scheduled_ts)
            flash(f"📅 {len(job_ids)} jobs scheduled for {dt.strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        flash(f"❌ Schedule failed: {e}")
    
    return redirect(url_for("discovered_page"))
```

## 5. Update base.html Sidebar

Add nav item:

```html
<a href='{{ url_for("discovered_page") }}' class='nav-item {% if request.endpoint == "discovered_page" %}active{% endif %}'>
    <i class='bi bi-search'></i>
    <span>Discovered</span>
</a>
```

## 6. Test

```cmd
python -m py_compile packages/storage/discovered_jobs.py

# Enable discovery mode in config.yaml:
# discovery:
#   enabled: true

python run_web.py
# Click Start
# Watch log for "🔍 DISCOVERY MODE"
# After scraping: visit http://localhost:5050/discovered
```

## 7. Workflow

```
Phase 1: SCRAPE
  Enable discovery_mode → Bot scrapes 50-100 jobs → Saved to DB

Phase 2: REVIEW
  Visit /discovered → Filter, search, sort by fit
  
Phase 3: SELECT
  Check checkboxes → "Mark for Apply"
  OR per-row buttons (✓ Apply / 💾 Save / ✗ Skip)

Phase 4: APPLY
  Click "Apply Now (N)" button
  Bot reads apply_queue.json
  Disable discovery mode → Apply only marked jobs
```

## 8. Anti-Breakage

- ✅ Separate `discovered_jobs` table (no conflict)
- ✅ Discovery mode is OPT-IN (default disabled)
- ✅ Apply queue isolated (`data/.control/apply_queue.json`)
- ✅ Backward compatible (existing apply flow unchanged)
- ✅ No breaking schema changes
