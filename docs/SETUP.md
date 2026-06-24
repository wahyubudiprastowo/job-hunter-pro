# 🛠️ Setup Guide — Step by Step

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required if running natively |
| Google Chrome | latest stable | Required (undetected-chromedriver auto-matches) |
| Docker Desktop | latest | Required if using Docker option |
| LinkedIn account | — | **Use a secondary account first to test!** |
| Base resume | `.pdf` | Drop into `resumes/base_resume.pdf` |

---

## 2. Clone & Configure

```bash
git clone <your-repo-url> job-hunter-pro
cd job-hunter-pro
cp .env.example .env
```

### Edit `.env`

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
LINKEDIN_TOTP_SECRET=                   # optional, if 2FA via authenticator app
HEADLESS=false                          # set to false on first run!
WEB_PORT=5050
```

### Edit `config.yaml`

The most important fields:

```yaml
mode: "semi_auto"                       # full_auto | semi_auto | safe_auto

platforms:
  linkedin:
    enabled: true
    max_apply_per_run: 10               # start small!
    search:
      queries: ["Cloud Engineer", "DevOps Engineer"]
      location: "Indonesia"
      remote: true
      easy_apply_only: true

filters:
  title_keywords_include: ["engineer", "devops", "cloud"]
  title_keywords_exclude: ["sales", "intern"]
  company_blacklist: []

personal:
  first_name: "..."
  last_name: "..."
  email: "..."
  phone: "..."
  years_experience: "..."
  ...

global_limits:
  total_apply_per_run: 10               # safety cap
```

### Drop your resume

```bash
cp /path/to/your-resume.pdf resumes/base_resume.pdf
```

---

## 3. Run

### 🐳 Docker (recommended)

```bash
docker compose up --build -d
docker compose logs -f         # watch output
```

Open http://localhost:5050.

### 🐍 Native (Linux / macOS)

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

### 🪟 Native (Windows / PowerShell)

```powershell
# Allow scripts for current session:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\scripts\run_local.ps1
```

---

## 4. First Run Walkthrough

1. Open http://localhost:5050 — you should see the dashboard
2. Click **🚀 Start**
3. A Chrome window opens (because `HEADLESS=false`)
4. Bot navigates to LinkedIn login
5. **If 2FA / CAPTCHA appears**: solve it in the visible window — bot will wait
6. After login, session is cached. Next runs won't ask again.
7. Bot starts searching + applying
8. Watch live logs in the dashboard

---

## 5. Production-ish Settings (after testing)

Once you've validated everything works:

```env
HEADLESS=true             # run silently in the background
```

```yaml
# config.yaml
mode: "full_auto"
global_limits:
  total_apply_per_run: 25 # increase gradually
stealth:
  pause_every_n_applications: 5
  pause_seconds: 90       # be conservative
```

---

## 6. Recommended Daily Workflow

| Time | Action |
|---|---|
| Morning | Click **Start** in dashboard |
| Bot runs | 15-45 min, ~10-25 applications |
| Bot done | Review **Unanswered Queue** → answer questions |
| Bot done | Review **Applications** tab — anything failed? |
| Evening | Optional: second run with different query |
