# PATCH 32.3 — Profile Reset Button Integration

## 🎯 Apa Yang Patch Ini Tambah

Tombol di Settings page untuk:
- 🔍 Lihat profile info (size, age, last used)
- 🔄 One-click reset profile (Indeed/LinkedIn)
- 🌐 Auto-launch Chrome dengan profile baru
- 📦 Auto-backup profile lama (timestamp)
- 🧹 Cleanup old backups (keep 3 latest)

---

## 📦 Files Touched

| File | Action | Lines |
|---|---|---|
| `packages/stealth/profile_manager.py` | NEW | ~280 |
| `apps/web/app.py` | UPDATE | +80 (3 routes) |
| `apps/web/templates/settings.html` | UPDATE | +120 (new section) |

---

## 1. Install Module

```cmd
copy patch\job-hunter-pro-patch32.3\packages\stealth\profile_manager.py packages\stealth\
```

## 2. Update `apps/web/app.py`

### 2a. Add imports

```python
from packages.stealth.profile_manager import (
    list_all_profiles, get_profile_info, reset_profile,
    backup_profile, cleanup_old_backups, get_profile_history,
)
```

### 2b. Add 3 routes

```python
@app.route("/settings/profiles", methods=["GET"])
def settings_profiles():
    """Show profile management page."""
    profiles = list_all_profiles()
    history = get_profile_history()[-10:]  # Last 10 events
    
    return render_template(
        "settings.html",
        active_section="profiles",
        profiles=profiles,
        profile_history=history,
        state=controller.get_state(),
    )


@app.route("/settings/profiles/reset/<platform>", methods=["POST"])
def settings_profile_reset(platform):
    """Reset platform profile with optional Chrome launch."""
    if platform not in ["linkedin", "indeed"]:
        flash(f"Unknown platform: {platform}")
        return redirect(url_for("settings_profiles"))
    
    # Don't reset if bot is running
    diag = controller.get_diagnostics()
    if diag["state"] == "running":
        flash("⚠️ Stop bot first before resetting profile")
        return redirect(url_for("settings_profiles"))
    
    launch = request.form.get("launch_chrome", "true").lower() == "true"
    
    result = reset_profile(platform, launch_chrome=launch)
    
    if result["success"]:
        flash(f"✅ {platform.title()} profile reset! {result['message']}")
    else:
        flash(f"❌ Reset failed: {result['message']}")
    
    return redirect(url_for("settings_profiles"))


@app.route("/settings/profiles/cleanup", methods=["POST"])
def settings_profile_cleanup():
    """Cleanup old profile backups."""
    keep = int(request.form.get("keep_count", "3"))
    deleted = cleanup_old_backups(keep_count=keep)
    flash(f"🧹 Cleaned up {deleted} old backups (kept newest {keep})")
    return redirect(url_for("settings_profiles"))
```

### 2c. Update `/settings` route to handle profiles section

In your existing `settings()` function, when `active_section == "profiles"`:

```python
if active_section == "profiles":
    profiles = list_all_profiles()
    history = get_profile_history()[-10:]
    context.update({
        "profiles": profiles,
        "profile_history": history,
    })
```

## 3. Update `apps/web/templates/settings.html`

### 3a. Add "Profiles" tab/pill

In your tabs navigation, add:

```html
<a href="?section=profiles" class="filter-pill {% if active_section == 'profiles' %}active{% endif %}">
    <i class="bi bi-person-badge"></i> Browser Profiles
</a>
```

### 3b. Add Profile Section

After existing sections (search, personal, behavior, credentials):

```html
{% if active_section == 'profiles' %}
<!-- PROFILES SECTION -->
<div class="card">
    <div class="card-header">
        <span><i class="bi bi-person-badge"></i> Chrome Profile Management</span>
        <small class="text-muted">Reset profiles when bot can't bypass Cloudflare</small>
    </div>
    <div class="card-body">
        
        <!-- Profile Cards -->
        <div class="d-grid" style="grid-template-columns: 1fr 1fr; gap: 16px;">
            {% for profile in profiles %}
            <div class="card" style="background: var(--color-bg);">
                <div class="card-body" style="padding: 16px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <div class="d-flex align-items-center gap-2">
                            <i class="bi bi-{% if profile.platform == 'linkedin' %}linkedin{% else %}briefcase{% endif %}" 
                               style="font-size: 24px; color: {% if profile.platform == 'linkedin' %}#0a66c2{% else %}#003a9b{% endif %};"></i>
                            <strong>{{ profile.platform|upper }}</strong>
                        </div>
                        {% if profile.exists %}
                            {% if profile.age_days > 30 %}
                                <span class="badge bg-warning">Old (recommend reset)</span>
                            {% elif profile.age_days > 14 %}
                                <span class="badge bg-info">Aging</span>
                            {% else %}
                                <span class="badge bg-success">Fresh</span>
                            {% endif %}
                        {% else %}
                            <span class="badge bg-secondary">Not Set Up</span>
                        {% endif %}
                    </div>
                    
                    {% if profile.exists %}
                    <table class="diag-table" style="width: 100%;">
                        <tr>
                            <td>Path:</td>
                            <td><code style="font-size: 11px;">{{ profile.path | truncate(40) }}</code></td>
                        </tr>
                        <tr>
                            <td>Size:</td>
                            <td>{{ profile.size_mb }} MB</td>
                        </tr>
                        <tr>
                            <td>Age:</td>
                            <td>{{ profile.age_days }} days</td>
                        </tr>
                        {% if profile.last_used %}
                        <tr>
                            <td>Last Used:</td>
                            <td>{{ profile.last_used | timeago }}</td>
                        </tr>
                        {% endif %}
                    </table>
                    {% else %}
                    <p class="text-muted small mb-3">Profile not initialized.</p>
                    {% endif %}
                    
                    <div class="d-flex gap-2 mt-3">
                        <form method="post" action="/settings/profiles/reset/{{ profile.platform }}" 
                              style="display: inline; flex: 1;"
                              onsubmit="return confirm('Reset {{ profile.platform }} profile? Current profile will be backed up. Chrome will launch for fresh setup.');">
                            <input type="hidden" name="launch_chrome" value="true">
                            <button type="submit" class="btn btn-danger btn-sm w-100"
                                    {% if state == 'running' %}disabled title="Stop bot first"{% endif %}>
                                <i class="bi bi-arrow-clockwise"></i> Reset Profile
                            </button>
                        </form>
                        
                        <form method="post" action="/settings/profiles/reset/{{ profile.platform }}" 
                              style="display: inline;">
                            <input type="hidden" name="launch_chrome" value="false">
                            <button type="submit" class="btn btn-outline-secondary btn-sm" 
                                    title="Reset only, don't launch Chrome"
                                    {% if state == 'running' %}disabled{% endif %}>
                                <i class="bi bi-folder-x"></i>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Cleanup Section -->
        <hr class="mt-4">
        <div class="d-flex align-items-center justify-content-between">
            <div>
                <strong>Backup Maintenance</strong>
                <p class="text-muted small mb-0">Delete old backups to free disk space</p>
            </div>
            <form method="post" action="/settings/profiles/cleanup" style="display: inline;">
                <input type="number" name="keep_count" value="3" min="1" max="10" 
                       class="search-input" style="width: 60px; display: inline-block;">
                <span class="small text-muted">keep newest</span>
                <button type="submit" class="btn btn-outline-secondary btn-sm ms-2">
                    <i class="bi bi-trash"></i> Cleanup
                </button>
            </form>
        </div>
        
        <!-- Profile History -->
        {% if profile_history %}
        <hr class="mt-4">
        <div>
            <strong>Recent Events</strong>
            <div class="mt-2" style="max-height: 200px; overflow-y: auto;">
                <table class="diag-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Platform</th>
                            <th>Event</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for event in profile_history|reverse %}
                        <tr>
                            <td>{{ event.timestamp | timeago }}</td>
                            <td><span class="badge bg-secondary">{{ event.platform }}</span></td>
                            <td>{{ event.event }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}
        
        <!-- Info Box -->
        <div class="alert alert-info mt-4">
            <strong><i class="bi bi-info-circle"></i> When to Reset?</strong>
            <ul class="mb-0 mt-2 small">
                <li><strong>Cloudflare blocks:</strong> Bot stuck at "Verify you are human" repeatedly</li>
                <li><strong>Profile aging:</strong> Profile > 30 days old, cookies expired</li>
                <li><strong>Anti-bot detection:</strong> "Additional Verification Required" + Ray ID</li>
                <li><strong>Account flagging:</strong> Platform asks unusual security questions</li>
            </ul>
            <hr class="my-2">
            <p class="mb-0 small">
                <strong>After reset:</strong> Chrome opens with fresh profile. 
                Sign in, browse 5-10 jobs naturally (5 mins), then close. 
                Cookies persist ~30 days.
            </p>
        </div>
    </div>
</div>
{% endif %}
```

## 4. Test

```cmd
python -m py_compile packages/stealth/profile_manager.py
python run_web.py
```

Visit http://localhost:5050/settings?section=profiles

You should see:
- 2 profile cards (LinkedIn + Indeed)
- Each card shows size, age, last used
- "Reset Profile" button per platform
- "Cleanup" button for old backups
- Recent events log

### Click Test
1. Click "Reset Profile" for Indeed
2. Confirmation dialog appears
3. Profile backed up (timestamped)
4. New empty profile created
5. Chrome launches automatically with new profile
6. Open Indeed in Chrome → complete CF + login + browse
7. Close Chrome
8. Return to dashboard → bot ready!

## 5. Workflow

```
User notices Cloudflare blocking Indeed:
   ↓
Visit /settings?section=profiles
   ↓
Click "Reset Profile" on Indeed card
   ↓
Backend:
   1. Stop check (bot must be idle)
   2. Backup profile: .chrome-profile-indeed.bak_20260625_140530
   3. Create fresh: .chrome-profile-indeed/
   4. Launch Chrome with new profile + indeed.com URL
   5. Record event in registry
   ↓
Chrome opens → User completes:
   - Cloudflare verification
   - Indeed login
   - Browse 5-10 jobs (humanize, 5 min)
   - Close Chrome
   ↓
Profile saved with fresh cookies + clean fingerprint
   ↓
Run bot → Should skip Cloudflare for ~30 days!
```

## 6. Anti-Breakage

- ✅ Helper module ADDITIVE
- ✅ Routes additive (new sub-routes /settings/profiles/*)
- ✅ Profile backups (rollback by manually moving back)
- ✅ Bot must be stopped (safety check)
- ✅ Auto-backup before reset (no data loss)
- ✅ Chrome launch optional (`launch_chrome=false`)
- ✅ Cleanup keeps 3 newest backups (configurable)

## 7. Future Enhancement Ideas

- 📅 Auto-reset reminder when profile > 25 days old
- 📊 Profile health score (cookie freshness, recent activity)
- 🔔 Telegram notification on profile reset
- 🤖 Auto-reset on Cloudflare detection in runner.py
- 🎯 Profile "warm-up" automation (auto-browse some jobs)
