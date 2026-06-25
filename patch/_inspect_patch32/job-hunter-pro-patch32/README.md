# 🔍 Patch 32 — Discovery & Curation Mode

## 🎯 Konsep

Pisahkan **scraping** dan **applying** menjadi 2 fase berbeda:

```
Phase 1: SCRAPE (read-only)
  Bot scrapes 50-100 jobs → Save metadata only
  
Phase 2: USER REVIEW
  Filter, sort, search di UI
  
Phase 3: SELECTIVE APPLY
  Check jobs yang relevant → Click "Apply Now"
  Bot applies only selected
```

## ✨ Features

### Discovery Mode
- **Scrape-only**: bot gak apply, cuma collect metadata
- **Deep scroll**: 15x scroll vs 8x normal
- **Cap 100 jobs/session**: balanced depth
- **Fit scoring**: tetap jalan via Patch 17
- **Duplicate detection**: UNIQUE (platform, job_id)

### Review UI (`/discovered`)
- **4 KPI cards**: Total, Selected, Saved, Avg Fit
- **6 status pills**: All / Pending / Selected / Auto-Apply / Saved / Applied
- **Multi-filter**: Search, Fit Score, Platform, Date
- **Sortable**: By fit_score desc (default)
- **Checkbox + Select All**: Per page bulk selection
- **5 bulk actions**: Mark for Apply, Auto-Apply, Save, Skip, Reset
- **Per-row actions**: Quick ✓ / 💾 / ✗ buttons
- **Job details**: Click title → open external link
- **Fit reasoning tooltip**: Hover info icon

### Apply Triggers
- **Immediate**: Click "Apply Now" → bot starts applying
- **Scheduled**: Set datetime → bot applies at specified time
- **Auto-rules**: Fit ≥ 90 = auto-queue, Fit < 30 = auto-skip

## 📦 Bundle Contents

| File | Lines | Purpose |
|---|---|---|
| `discovered_jobs.py` | ~280 | DB layer with 7 functions |
| `discovered.html` | ~250 | Review UI template |
| `INTEGRATION_SNIPPETS.md` | - | 8-step integration guide |
| `apply.cmd` | - | Auto-installer |

## 🚀 Cara Pakai

### Step 1: Install (1 min)
```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch32.zip

cd job-hunter-pro-patch32
apply.cmd
```

### Step 2: Integration (30 min)
Follow `INTEGRATION_SNIPPETS.md`:
- Add config section
- Update `runner.py` (discovery branch)
- Update `app.py` (5 routes)
- Add nav item to `base.html`

### Step 3: Test
1. Set `discovery.enabled: true` in config
2. Restart bot → Click Start
3. Watch log for "🔍 DISCOVERY MODE"
4. After scraping, visit `/discovered`
5. Filter + select jobs
6. Click "Apply Now"

## 🗄️ Database Schema

```sql
CREATE TABLE discovered_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    job_id TEXT NOT NULL,
    title, company, location, url TEXT,
    description, salary TEXT,
    fit_score INTEGER,
    fit_reasoning TEXT,
    is_easy_apply INTEGER,
    status TEXT DEFAULT 'discovered',
    scheduled_at INTEGER,
    discovered_at INTEGER NOT NULL,
    reviewed_at INTEGER,
    applied_at INTEGER,
    user_notes TEXT,
    metadata TEXT,
    UNIQUE(platform, job_id)
);
```

## 🎨 Lifecycle States

```
discovered (default) → selected (user marked)
                    ├→ auto_apply (rule-based or scheduled)
                    ├→ saved (for later)
                    ├→ skipped (user dismissed)
                    └→ applied (move to applications table)
```

## ✅ Anti-Breakage

- ✅ NEW table (no schema conflict)
- ✅ Discovery mode OPT-IN (default disabled)
- ✅ Apply queue isolated (JSON file)
- ✅ Backward compat (existing flow unchanged)
- ✅ Idempotent saves (UNIQUE constraint)
- ✅ Cleanup helper (delete old > 30 days)

## 📊 Expected Workflow

```
Day 1 morning: Run discovery (1 hour, 100 jobs scraped)
Day 1 review: Browse list, check 20 favorites
Day 1 trigger: Click "Apply Now" → bot applies 20 jobs
Day 1 night: Check Telegram for confirmations

Day 2: Repeat with different queries
```

## 🎯 Benefits

| Aspect | Auto-Apply (Old) | Discovery (New) |
|---|---|---|
| Rate limit risk | High | LOW (just scrape) |
| Job quality | Variable | Curated by user |
| Response rate | 30-40% | 50-70% expected |
| Time investment | 0 (set & forget) | 15 min review |
| Control | Minimal | Full |

## 🔗 Related

- Patch 17 — Fit Scoring (used in discovery)
- Patch 19 — Rate Limiter (discovery doesn't trigger apply cap)
- Patch 21 v2 — UI (sidebar nav)
- Patch 22 — Indeed Extractor (multi-platform discovery)
- Patch 28 — Telegram (notify discovery complete)
