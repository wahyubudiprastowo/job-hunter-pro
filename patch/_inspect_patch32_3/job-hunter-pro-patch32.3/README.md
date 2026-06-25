# 🔄 Patch 32.3 — Browser Profile Reset Button

## 🎯 What This Solves

PowerShell drama bikin reset profile susah. Button di Settings page = **1 click solution**!

Click "Reset Profile" untuk Indeed/LinkedIn → otomatis:
1. ✅ Backup profile lama (timestamped, restorable)
2. ✅ Create fresh profile directory
3. ✅ Launch Chrome dengan profile baru
4. ✅ Open Indeed.com / LinkedIn.com URL
5. ✅ User complete login manual
6. ✅ Close Chrome → ready untuk bot

## 📦 Bundle Contents

| File | Lines | Purpose |
|---|---|---|
| `profile_manager.py` | ~280 | Backup/reset/launch helper |
| `INTEGRATION_SNIPPETS.md` | - | Step-by-step |
| `apply.cmd` | - | Auto-installer |
| `README.md` | - | This file |

## 🎨 UI Preview

### Settings → Browser Profiles Tab
```
┌──────────────────────────────────────────────────────────────────┐
│ 👤 Chrome Profile Management                                      │
│ Reset profiles when bot can't bypass Cloudflare                   │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────┐         │
│ │ 🔵 LINKEDIN  [Fresh]    │  │ 🔷 INDEED [Old⚠️]       │         │
│ │ Path: .chrome-profile-..│  │ Path: .chrome-profile-..│         │
│ │ Size: 145 MB            │  │ Size: 287 MB            │         │
│ │ Age: 5 days             │  │ Age: 35 days            │         │
│ │ Last: 2 hours ago       │  │ Last: 3 days ago        │         │
│ │ [🔴 Reset Profile] [📁] │  │ [🔴 Reset Profile] [📁] │         │
│ └─────────────────────────┘  └─────────────────────────┘         │
├──────────────────────────────────────────────────────────────────┤
│ Backup Maintenance                          [3] keep newest [🧹]  │
├──────────────────────────────────────────────────────────────────┤
│ ℹ️  When to Reset?                                                │
│ • Cloudflare blocks repeatedly                                    │
│ • Profile aging > 30 days                                         │
│ • Anti-bot detection (Ray ID)                                     │
│ • Account flagging                                                │
└──────────────────────────────────────────────────────────────────┘
```

### After Click "Reset Profile"
```
1. Confirmation dialog: "Reset indeed profile?"
2. Backend backs up profile to .chrome-profile-indeed.bak_20260625_140530
3. Creates new fresh .chrome-profile-indeed/
4. Launches Chrome dengan window terbuka di indeed.com
5. Flash message: "✅ indeed profile reset! Chrome launched (PID 12345)..."
```

## 🚀 Cara Pakai

### Step 1: Install (1 menit)
```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch
REM Extract job-hunter-pro-patch32.3.zip

cd job-hunter-pro-patch32.3
apply.cmd
```

### Step 2: Integration (15 menit)
Follow INTEGRATION_SNIPPETS.md:
- Add 3 routes to `app.py`
- Add Profiles section ke `settings.html`
- Add tab navigation

### Step 3: Test
1. Visit `http://localhost:5050/settings?section=profiles`
2. Lihat 2 cards profile (LinkedIn + Indeed)
3. Click "Reset Profile" untuk Indeed
4. Confirm dialog → OK
5. Chrome opens dengan fresh profile
6. Complete Cloudflare + login + browse 5-10 jobs
7. Close Chrome
8. Bot ready dengan profile baru!

## ✨ Key Features

### 🔄 One-Click Reset
- Backup old profile dengan timestamp
- Create fresh profile
- Launch Chrome otomatis
- No PowerShell drama

### 📊 Profile Info
- Size in MB
- Age in days (with status badge: Fresh/Aging/Old)
- Last used timestamp
- Status badges (color-coded)

### 🛡️ Safety
- Must stop bot first (safety check)
- Auto-backup (rollback possible)
- Confirmation dialog
- Profile path displayed

### 📜 History Tracking
- Every reset/backup logged
- Last 10 events visible
- Recent events table

### 🧹 Backup Cleanup
- Configurable: keep N newest
- One-click cleanup
- Disk space management

## 🔧 Profile Manager Functions

```python
from packages.stealth.profile_manager import (
    list_all_profiles,    # Get all profiles info
    get_profile_info,     # Single profile info
    backup_profile,       # Backup with timestamp
    reset_profile,        # Backup + create fresh + launch Chrome
    cleanup_old_backups,  # Keep N newest
    get_profile_history,  # Event log
)

# Programmatic usage:
result = reset_profile("indeed", launch_chrome=True)
print(result["message"])  # "Chrome launched (PID 12345)..."
```

## ✅ Anti-Breakage

- ✅ Helper module ADDITIVE
- ✅ Routes additive
- ✅ Profile backups (rollback by rename)
- ✅ Bot safety check (must be idle)
- ✅ Auto-backup before reset
- ✅ No DB changes
- ✅ No config.yaml changes

## 🆘 Rollback

If patch causes issues:
- Manually rename `.chrome-profile-indeed.bak_*` back to `.chrome-profile-indeed`
- Delete `profile_manager.py`
- Remove routes from `app.py`

## 🔗 Related

- Patch 31.2 — Cloudflare workaround (this is the UI version)
- Patch 28.1 — Settings page (this adds new section)
- Patch 22 — Indeed Extractor (uses these profiles)

## 🎯 What's Next

After Patch 32.3:
- ⏭️ Auto-reset reminder (profile > 25 days)
- ⏭️ Telegram alert on profile reset
- ⏭️ Profile health score
- ⏭️ Auto-detect Cloudflare → suggest reset
