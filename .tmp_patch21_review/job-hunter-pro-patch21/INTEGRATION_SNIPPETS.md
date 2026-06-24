# PATCH 21 — UI Modernization Integration Guide

## 📦 What's Included

| File | Purpose |
|---|---|
| `apps/web/static/styles.css` | NEW — Modern CSS (~18KB) |
| `apps/web/templates/base.html` | REPLACED — Sidebar layout with Inter font |
| `apps/web/templates/dashboard.html` | REPLACED — KPI cards + ApexCharts |
| `apps/web/templates/applications.html` | REPLACED — Modern table with filters |
| `apps/web/templates/application_detail.html` | REPLACED — Fit score visualization |
| `apps/web/templates/questions.html` | REPLACED — Inline answer forms |

## 🎨 Design Highlights

- **Inter font** via Google Fonts (modern, readable)
- **Bootstrap Icons** via CDN (consistent iconography)
- **ApexCharts** via CDN (interactive charts)
- **Tailwind-inspired colors** (slate/sky/emerald palette)
- **Sidebar navigation** (250px, collapsible on mobile)
- **5 KPI cards** with gradient borders + hover effects
- **2 chart widgets** (14-day bar + skip reasons donut)
- **Rate limit banner** (Patch 19 integration)
- **Fit score visualization** (Patch 17 integration)

## 🚀 How to Apply

### Step 1: Backup current UI (RECOMMENDED)
```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
mkdir "apps\web\templates.bak_$ts" 2>$null
Copy-Item apps\web\templates\*.html "apps\web\templates.bak_$ts\" -Force
```

### Step 2: Install Patch 21 files

```powershell
# Copy static folder
mkdir apps\web\static 2>$null
Copy-Item patch\job-hunter-pro-patch21\apps\web\static\styles.css apps\web\static\styles.css

# Copy templates (overwrites existing)
Copy-Item patch\job-hunter-pro-patch21\apps\web\templates\*.html apps\web\templates\ -Force
```

### Step 3: Update `apps/web/app.py` — Backend extensions

Add **stats_today** function and **avg_fit_score** + **apps_14days** + **skip_reasons** data to dashboard route.

#### 3a. Add helper functions at top:

```python
from datetime import datetime, timedelta, date

def _get_stats_today(conn):
    """Get today's applied + skipped counts."""
    today = date.today().strftime("%Y-%m-%d")
    try:
        cursor = conn.execute('''
            SELECT status, COUNT(*) as cnt
            FROM applications
            WHERE DATE(created_at) = ?
            GROUP BY status
        ''', (today,))
        result = {row[0]: row[1] for row in cursor.fetchall()}
        return {
            "applied": result.get("applied", 0),
            "skipped": result.get("skipped", 0) + result.get("external", 0),
            "failed": result.get("failed", 0),
        }
    except Exception:
        return {"applied": 0, "skipped": 0, "failed": 0}

def _get_apps_14days(conn):
    """Get applied count per day for last 14 days."""
    labels = []
    data = []
    try:
        for i in range(13, -1, -1):
            target_date = (date.today() - timedelta(days=i))
            label = target_date.strftime("%m-%d")
            cursor = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status='applied' AND DATE(created_at)=?",
                (target_date.strftime("%Y-%m-%d"),)
            )
            count = cursor.fetchone()[0]
            labels.append(label)
            data.append(count)
    except Exception:
        pass
    return {"labels": labels, "data": data}

def _get_skip_reasons(conn):
    """Get skip reason breakdown."""
    try:
        cursor = conn.execute('''
            SELECT skip_reason, COUNT(*) as cnt
            FROM applications
            WHERE status IN ('skipped', 'external') AND skip_reason IS NOT NULL
            GROUP BY skip_reason
            ORDER BY cnt DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        labels = [(r[0] or 'other').replace('_', ' ').title() for r in rows]
        data = [r[1] for r in rows]
        return {"labels": labels, "data": data}
    except Exception:
        return {"labels": [], "data": []}

def _get_avg_fit_score(conn):
    """Get average fit score (or None)."""
    try:
        cursor = conn.execute(
            "SELECT AVG(fit_score) FROM applications WHERE fit_score IS NOT NULL"
        )
        avg = cursor.fetchone()[0]
        return int(avg) if avg is not None else None
    except Exception:
        return None
```

#### 3b. Update dashboard route to include new data:

```python
@app.route("/")
def dashboard():
    stats = store.get_stats()
    recent = store.list_applications(limit=10)
    runs = store.recent_runs(limit=5)
    latest_run = runs[0] if runs else None
    unanswered = load_unanswered()
    diag = controller.get_diagnostics()
    latest_screenshot = _latest_debug_screenshot()
    
    # Patch 21: New data
    conn = store._conn if hasattr(store, '_conn') else None
    stats_today = _get_stats_today(conn) if conn else None
    avg_fit_score = _get_avg_fit_score(conn) if conn else None
    
    # Patch 19: Rate limit status (if integrated)
    rate_limit_status = None
    try:
        import yaml
        cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
        gl = cfg.get("global_limits", {})
        from packages.extractors.rate_limiter import get_status_for_dashboard
        rate_limit_status = get_status_for_dashboard(conn, "linkedin", gl)
    except Exception:
        pass
    
    return render_template(
        "dashboard.html",
        stats=stats, recent=recent, runs=runs, latest_run=latest_run,
        unanswered=unanswered, state=diag["state"], diag=diag,
        latest_screenshot=latest_screenshot,
        # New Patch 21 context:
        stats_today=stats_today,
        avg_fit_score=avg_fit_score,
        rate_limit_status=rate_limit_status,
    )
```

#### 3c. Update `/api/dashboard` to send chart data:

```python
@app.route("/api/dashboard")
def api_dashboard():
    unanswered = load_unanswered()
    recent = store.list_applications(limit=10)
    runs = store.recent_runs(limit=1)
    latest_run = runs[0] if runs else None
    
    conn = store._conn if hasattr(store, '_conn') else None
    
    for row in recent:
        row["created_at_display"] = _format_local_datetime(row.get("created_at"))
    
    if latest_run:
        latest_run["started_at_display"] = _format_local_datetime(latest_run.get("started_at"))
        latest_run["finished_at_display"] = _format_local_datetime(latest_run.get("finished_at"))
    
    return jsonify({
        "state": controller.get_state(),
        "stats": store.get_stats(),
        "diag": controller.get_diagnostics(),
        "recent": recent,
        "latest_run": latest_run,
        "latest_screenshot": _latest_debug_screenshot(),
        "unanswered_count": len(unanswered),
        # Patch 21: Chart data
        "stats_today": _get_stats_today(conn) if conn else None,
        "avg_fit_score": _get_avg_fit_score(conn) if conn else None,
        "apps_14days": _get_apps_14days(conn) if conn else None,
        "skip_reasons": _get_skip_reasons(conn) if conn else None,
    })
```

### Step 4: Test

```powershell
# Start bot web UI
python run_web.py

# Open browser
# http://localhost:5050

# Visit:
# - /          → Dashboard (KPI cards + charts)
# - /applications → History (filterable table)
# - /application/1 → Detail (fit score visual)
# - /questions → Question bank
```

## 🔄 Rollback

If you don't like the new UI:

```powershell
# Restore from backup
$bak = Get-ChildItem apps\web\templates.bak_* | Sort-Object Name -Descending | Select-Object -First 1
Copy-Item "$($bak.FullName)\*.html" apps\web\templates\ -Force

# Remove styles.css
Remove-Item apps\web\static\styles.css
```

## 🛡️ Anti-Breakage Compliance

- ✅ ADDITIVE (new styles.css, new sidebar layout)
- ✅ Template-only changes (no backend logic changes if step 3 skipped)
- ✅ Backward compatible (charts gracefully handle missing data)
- ✅ Optional Patch 19 rate limit banner (only shows if data exists)
- ✅ Optional Patch 17 fit score (only shows if column populated)
- ✅ No DB schema changes
- ✅ No credential touches
- ✅ Existing API endpoints unchanged

## 📸 Visual Comparison

### Before (v1):
- Bootstrap 5 with basic Vanilla styling
- Top nav, no sidebar
- Cards with flat backgrounds
- Generic table with no charts
- Basic logs display

### After (v2 — Patch 21):
- Inter font, custom CSS
- Persistent sidebar with active state
- KPI cards with gradient borders
- ApexCharts: bar chart (14 days) + donut (skip reasons)
- Modern color palette (slate/sky/emerald)
- Rate limit status banner with progress bar
- Fit score visualization (color-coded)
- Hover effects + smooth transitions
- Mobile responsive (sidebar collapses)

## 🎯 What's Next After Patch 21

- **Patch 22** — Phase 4a Indeed Extractor (use new UI to monitor)
- **Patch 23** — Phase 3a Ghosting Detector (add to UI)
- **Patch 24** — Phase 3d Telegram Notifications

The UI is now polished and ready for additional features to be added.
