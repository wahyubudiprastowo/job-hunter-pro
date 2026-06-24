# PATCH 28.1 — Real Settings Integration

## 🎯 Apa Yang Patch Ini Solve

Saat ini Settings page **cuma cantik** tapi:
- ❌ Tidak baca dari `config.yaml` yang sebenarnya
- ❌ Tidak baca dari `.env` (credentials hilang)
- ❌ Tidak bisa save perubahan
- ❌ Harus edit file manual = error-prone

Patch ini bikin Settings page **benar-benar berfungsi**:
- ✅ Auto-load dari `config.yaml` dan `.env`
- ✅ Edit langsung di UI tanpa text editor
- ✅ Auto-backup sebelum save
- ✅ Validation sebelum write
- ✅ Secret masking untuk passwords/tokens
- ✅ Section-based save (cuma update section yang berubah)

## 📦 Files Touched

| File | Action | Lines |
|---|---|---|
| `apps/web/settings_api.py` | NEW | ~250 |
| `apps/web/app.py` | UPDATE | +120 |
| `apps/web/templates/settings.html` | NEW | ~600 |
| `apps/web/templates/base.html` | UPDATE | +3 (nav link) |

## 🚀 Cara Pakai

### Step 1: Copy module
```cmd
copy patch\job-hunter-pro-patch28.1\apps\web\settings_api.py apps\web\settings_api.py
copy patch\job-hunter-pro-patch28.1\apps\web\templates\settings.html apps\web\templates\settings.html
```

### Step 2: Update `apps/web/app.py`

ADD imports:

```python
from apps.web.settings_api import (
    load_config, save_config, update_config_section,
    load_env, save_env, get_env_for_display, validate_config,
    SECRET_KEYS,
)
```

ADD new routes:

```python
@app.route("/settings")
def settings():
    """Render settings page with current config and env."""
    try:
        config = load_config()
        env_display = get_env_for_display()
        warnings = validate_config(config)
        
        # Get active section from query param
        active_section = request.args.get("section", "search")
        
        return render_template(
            "settings.html",
            config=config,
            env_display=env_display,
            warnings=warnings,
            active_section=active_section,
            state=controller.get_state(),
        )
    except Exception as e:
        flash(f"Failed to load settings: {e}")
        return redirect(url_for("dashboard"))


@app.route("/settings/save/<section>", methods=["POST"])
def settings_save(section):
    """Save a section of config.yaml."""
    try:
        # Parse form data into appropriate dict structure
        form_data = request.form.to_dict(flat=False)
        
        if section == "search":
            # Search filters
            new_values = {
                "filters": {
                    "title_keywords_include": _parse_list(form_data.get("title_include", [""])[0]),
                    "title_keywords_exclude": _parse_list(form_data.get("title_exclude", [""])[0]),
                    "description_keywords_exclude": _parse_list(form_data.get("description_exclude", [""])[0]),
                    "company_blacklist": _parse_list(form_data.get("company_blacklist", [""])[0]),
                    "min_salary": int(form_data.get("min_salary", ["0"])[0] or 0),
                    "skip_already_applied": "skip_already_applied" in form_data,
                }
            }
            # Update platforms.linkedin.search queries
            queries = _parse_list(form_data.get("queries", [""])[0])
            locations = form_data.get("location", [""])[0]
            
            config = load_config()
            config.setdefault("filters", {}).update(new_values["filters"])
            
            # Update each platform's search settings
            for platform in config.get("platforms", {}):
                if queries:
                    config["platforms"][platform].setdefault("search", {})["queries"] = queries
                if locations:
                    config["platforms"][platform]["search"]["location"] = locations
            
            # Update global limits
            if "max_apply_per_run" in form_data:
                for platform in config.get("platforms", {}):
                    config["platforms"][platform]["max_apply_per_run"] = int(form_data["max_apply_per_run"][0])
            
            success, msg = save_config(config)
            
        elif section == "personal":
            new_values = {
                "first_name": form_data.get("first_name", [""])[0],
                "last_name": form_data.get("last_name", [""])[0],
                "email": form_data.get("email", [""])[0],
                "phone": form_data.get("phone", [""])[0],
                "phone_country_code": form_data.get("phone_country_code", [""])[0],
                "city": form_data.get("city", [""])[0],
                "country": form_data.get("country", [""])[0],
                "linkedin_url": form_data.get("linkedin_url", [""])[0],
                "github_url": form_data.get("github_url", [""])[0],
                "portfolio_url": form_data.get("portfolio_url", [""])[0],
                "years_experience": form_data.get("years_experience", [""])[0],
                "current_company": form_data.get("current_company", [""])[0],
                "current_title": form_data.get("current_title", [""])[0],
                "highest_education": form_data.get("highest_education", [""])[0],
                "authorized_to_work": form_data.get("authorized_to_work", [""])[0],
                "require_sponsorship": form_data.get("require_sponsorship", [""])[0],
                "willing_to_relocate": form_data.get("willing_to_relocate", [""])[0],
                "notice_period_days": form_data.get("notice_period_days", [""])[0],
                "expected_salary": form_data.get("expected_salary", [""])[0],
                "current_salary": form_data.get("current_salary", [""])[0],
            }
            success, msg = update_config_section("personal", new_values)
            
        elif section == "behavior":
            # settings.yaml equivalent — stealth + bot behavior
            stealth_updates = {
                "min_delay_sec": float(form_data.get("min_delay_sec", ["2"])[0]),
                "max_delay_sec": float(form_data.get("max_delay_sec", ["4.5"])[0]),
                "pause_every_n_applications": int(form_data.get("pause_every_n", ["5"])[0]),
                "pause_seconds": int(form_data.get("pause_seconds", ["60"])[0]),
            }
            ai_updates = {
                "enabled": "ai_enabled" in form_data,
                "model": form_data.get("ai_model", [""])[0],
                "resume_tailoring": "resume_tailoring" in form_data,
                "cover_letter": "cover_letter" in form_data,
                "fit_scoring": "fit_scoring" in form_data,
            }
            
            config = load_config()
            config.setdefault("stealth", {}).update(stealth_updates)
            config.setdefault("ai", {}).update(ai_updates)
            
            # Headless toggle goes to .env
            headless = "headless" in form_data
            env = load_env()
            env["HEADLESS"] = "true" if headless else "false"
            save_env(env)
            
            success, msg = save_config(config)
            
        elif section == "credentials":
            # .env credentials
            env = load_env()
            updates = {}
            
            for key in ["LINKEDIN_EMAIL", "INDEED_EMAIL", "AI_API_KEY", "AI_BASE_URL",
                        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "CAPTCHA_API_KEY",
                        "FLASK_SECRET_KEY", "WEB_HOST", "WEB_PORT", "LOG_LEVEL"]:
                form_key = key.lower()
                if form_key in form_data:
                    value = form_data[form_key][0]
                    # Skip if user left the masked placeholder
                    if not value.startswith("****"):
                        updates[key] = value
            
            # Passwords - only update if user typed new value
            for key in ["LINKEDIN_PASSWORD", "INDEED_PASSWORD", "LINKEDIN_TOTP_SECRET"]:
                form_key = key.lower()
                if form_key in form_data and form_data[form_key][0]:
                    updates[key] = form_data[form_key][0]
            
            env.update(updates)
            success, msg = save_env(env)
            
        else:
            flash(f"Unknown section: {section}")
            return redirect(url_for("settings"))
        
        if success:
            flash(f"✅ Saved {section}: {msg}")
        else:
            flash(f"❌ Save failed: {msg}")
        
        return redirect(url_for("settings", section=section))
    
    except Exception as e:
        flash(f"❌ Save error: {e}")
        return redirect(url_for("settings", section=section))


def _parse_list(value: str) -> list:
    """Parse comma or newline separated list."""
    if not value:
        return []
    items = value.replace("\r", "").replace("\n", ",").split(",")
    return [item.strip() for item in items if item.strip()]
```

### Step 3: Update Base Template Sidebar

In `base.html`, add Settings link if not yet present:

```html
<a href="{{ url_for('settings') }}" class="nav-item {% if request.endpoint == 'settings' %}active{% endif %}">
  <i class="bi bi-gear-fill"></i>
  <span>Settings</span>
</a>
```

### Step 4: Test

```cmd
python -m py_compile apps/web/settings_api.py apps/web/app.py
python run_web.py
```

Open http://localhost:5050/settings

You should see 4 tabs:
1. **Search** — Job titles, locations, filters, blacklist
2. **Personal** — Profile, contact, work info
3. **Behavior** — AI, stealth, headless mode
4. **Credentials** — Email/passwords with masking

## 🛡️ Safety Features

### Auto-Backup
Every save creates timestamped backup in `data/.settings_backups/`:
- `config_20260624_140530.yaml`
- `env_20260624_140530`

### Secret Masking
Passwords and tokens displayed as `wahy****0719`. Original kept untouched unless you type new value.

### Validation
Warnings displayed for:
- Missing required sections
- No platforms enabled
- AI enabled but no model
- Resume file not found

### Comment Preservation
`.env` saves preserve comments and structure:
```bash
# === LinkedIn Credentials ===   <-- preserved
LINKEDIN_EMAIL=...                <-- updated
LINKEDIN_PASSWORD=...             <-- updated
```

### Rollback
Manual rollback via PowerShell:
```powershell
$bak = Get-ChildItem data\.settings_backups\config_*.yaml | Sort-Object Name -Descending | Select-Object -First 1
Copy-Item $bak.FullName config.yaml
```

## ✅ Anti-Breakage Compliance

- ✅ Settings module is ADDITIVE
- ✅ Settings page is NEW route
- ✅ No breaking changes to existing dashboard
- ✅ Auto-backup before every write
- ✅ Validation before write
- ✅ Backward compatible (no UI changes break existing setup)
- ✅ Secret masking (no plaintext leakage in UI source)
- ✅ Comment-preserving .env writer

## 🆘 Rollback

If issues:
1. Don't use `/settings` page
2. Edit files manually as before
3. Or restore from backup folder

## 🎯 What's Next

After Patch 28.1:
- All settings editable via UI
- No more manual file editing
- Bot startup picks up changes immediately (config reloaded on each run)
