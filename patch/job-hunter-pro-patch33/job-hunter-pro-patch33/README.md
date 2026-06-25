# 🪟 Patch 33 — Glassdoor Extractor (Phase 4b)

## 🎯 Apa Yang Patch Ini Tambah

Multi-platform expansion: LinkedIn + Indeed + **Glassdoor**!

Glassdoor unik karena:
- ✅ Salary data per job (best in market)
- ✅ Company rating (1-5 stars)
- ✅ Company reviews (insider knowledge)
- ✅ 9M+ active job listings

## 📦 Bundle Contents

| File | Lines | Purpose |
|---|---|---|
| `glassdoor.py` | ~700 | Full extractor with login/search/apply |
| `prewarm_glassdoor.py` | ~80 | Profile setup script |
| `INTEGRATION_SNIPPETS.md` | - | Step-by-step integration |
| `apply.cmd` | - | Auto-installer |
| `README.md` | - | This file |

## ✨ Features (per user choices)

### Login: Auto-detect (Email OR Google)
- Tries Google OAuth first (if Chrome profile has Google session)
- Falls back to Email/Password
- Reuses Chrome profile cookies (~30 days)

### Region Auto-Detect
Based on location keyword in config:
- "Singapore" → glassdoor.sg
- "London" → glassdoor.co.uk
- "Berlin" → glassdoor.de
- "Toronto" → glassdoor.ca
- Default: glassdoor.com

### Easy Apply Only (1-click)
- Detects Easy Apply button
- Handles iframe modal (similar to LinkedIn/Indeed)
- Multi-step form auto-fill
- AI question fallback (reuses Patch 3)

### Salary → Fit Score Boost
Glassdoor unique salary data integrated to fit scoring:
- Parses "$120K - $150K (Glassdoor est.)" → structured data
- Converts to annual USD (with currency conversion)
- Boost +5 for >$120k, +10 for >$180k

## 🏗️ Architecture Reuse (~75%)

| Component | Source |
|---|---|
| Base extractor pattern | Patch 22 Indeed |
| Cloudflare handling | Patch 31.2 helper |
| Profile management | Patch 32.3 |
| AI question fallback | Patch 3 |
| Fit scoring | Patch 17 |
| Discovery mode | Patch 32 |
| Rate limiter | Patch 19 |

## 🚀 Quick Start

### Step 1: Install (1 menit)
```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch33.zip

cd job-hunter-pro-patch33
apply.cmd
```

### Step 2: Pre-warm Glassdoor Profile (10 menit)
```cmd
python scripts\prewarm_glassdoor.py
```
- Browser opens Glassdoor
- Sign in (Google OAuth or Email)
- Complete profile setup
- Browse 5-10 jobs
- Close browser

### Step 3: Integration (30 menit)
Follow INTEGRATION_SNIPPETS.md:
- Add config section
- Update runner.py registry
- Update profile_manager.py
- Optional: Update discovered.html for button

### Step 4: Test
```cmd
python run_web.py
```

Visit `/discovered`, enable discovery mode, scrape Glassdoor!

## 🌐 Supported Regions

```python
GLASSDOOR_REGIONS = {
    "us": "https://www.glassdoor.com",
    "uk": "https://www.glassdoor.co.uk",
    "ca": "https://www.glassdoor.ca",
    "de": "https://www.glassdoor.de",
    "fr": "https://www.glassdoor.fr",
    "sg": "https://www.glassdoor.sg",
    "in": "https://www.glassdoor.co.in",
    "au": "https://www.glassdoor.com.au",
    "nl": "https://www.glassdoor.nl",
    "ie": "https://www.glassdoor.ie",
}
```

Auto-detect from location keyword. Override with `region: "sg"` (etc.) in config.

## 💰 Salary Parser Examples

```python
# Input: "$120K - $150K (Glassdoor est.)"
# Output:
{
    "min": 120000,
    "max": 150000,
    "currency": "USD",
    "period": "year",
    "is_estimated": True,
}

# Input: "S$100K - S$140K Per Year"
# Output:
{
    "min": 100000,
    "max": 140000,
    "currency": "SGD",
    "period": "year",
    "is_estimated": False,
}
```

## ✅ Anti-Breakage

- ✅ Module ADDITIVE (new file)
- ✅ Backward compatible (existing extractors untouched)
- ✅ Optional dependency (try/except for missing module)
- ✅ Region auto-detect with safe fallback
- ✅ Cloudflare integration
- ✅ No DB schema changes

## ⚠️ Important Notes

### Pre-warm REQUIRED
Glassdoor has Cloudflare (like Indeed). **MUST run prewarm script first** for clean profile.

### Cookies Expire ~30 days
Re-run prewarm if Cloudflare blocks bot again.

### Easy Apply Availability
Not all jobs have Easy Apply. External jobs marked as `EXTERNAL` status (tracked, not applied).

### Google OAuth Limitations
Bot can't auto-login Google itself. User must have Google session active in Chrome profile.

## 🆘 Rollback

Remove `glassdoor.py` + `prewarm_glassdoor.py`. Remove config section. No DB changes.

## 🔗 Related

- Patch 22 — Indeed Extractor (similar pattern)
- Patch 31.2 — Cloudflare helper (reused)
- Patch 32.3 — Profile management (reused)
- Patch 17 — Fit Scoring (salary boost integration)

## 🎯 What's Next After Patch 33

- ⏭️ Patch 34 — JobStreet (SEA market, less Cloudflare)
- ⏭️ Patch 35 — Wellfound (Startup focus)
- ⏭️ Patch 36 — Greenhouse/Lever ATS direct apply
