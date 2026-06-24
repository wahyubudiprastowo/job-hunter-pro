# 🤖 Job-Hunter Pro — Phase 1

**Plugin-based LinkedIn Easy Apply bot** with a Flask web dashboard, SQLite history, 
fuzzy answer bank, anti-detection (undetected-chromedriver), and a clean
`BaseExtractor` interface so you can add Indeed / Glassdoor / JobStreet later
just by **dropping in a new file**.

> ⚠️ **Disclaimer**: Automating LinkedIn may violate their [User Agreement § 8.2](https://www.linkedin.com/legal/user-agreement).
> Use a throwaway account first. You assume all risk.

---

## 📦 What's Inside Phase 1

| Component | Status |
|---|:---:|
| `BaseExtractor` abstract interface | ✅ |
| LinkedIn extractor (login → search → Easy Apply) | ✅ |
| Filters (title/desc/company/salary/blacklist) | ✅ |
| Fuzzy answer bank + unanswered question queue | ✅ |
| SQLite + SQLAlchemy storage | ✅ |
| Flask web dashboard (history, Q&A editor, controls) | ✅ |
| 3 operating modes: `full_auto` / `semi_auto` / `safe_auto` | ✅ |
| Pause / Resume / Stop signaling (file-based) | ✅ |
| Anti-detection (undetected-chromedriver + humanizer) | ✅ |
| Docker Compose | ✅ |
| Native run scripts (Windows + Linux/macOS) | ✅ |
| AI tailoring (resume + cover letter) | ⏭️ Phase 2 |
| Indeed / Glassdoor / JobStreet extractors | ⏭️ Phase 4 |

---

## 🚀 Quick Start — 3 Ways

### Option A — Docker (recommended)

```bash
# 1) Configure
cp .env.example .env
nano .env          # fill LINKEDIN_EMAIL, LINKEDIN_PASSWORD

# 2) Edit your search preferences
nano config.yaml   # queries, location, filters

# 3) Drop your base resume PDF
cp /path/to/your/resume.pdf resumes/base_resume.pdf

# 4) Run
docker compose up --build -d

# 5) Open dashboard
open http://localhost:5050
```

Click **🚀 Start** in the dashboard.

> **First-time login**: LinkedIn often asks for 2FA or CAPTCHA. Set `HEADLESS=false`
> in `.env` for the first run so you can solve it in the visible browser window.
> After login, the session is cached in the `chrome-profile` Docker volume —
> you can switch back to `HEADLESS=true` for subsequent runs.

### Option B — Native Python (Linux/macOS)

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

### Option C — Native Python (Windows / PowerShell)

```powershell
.\scripts\run_local.ps1
```

---

## 🎛️ The 3 Operating Modes

Set `mode:` in `config.yaml`:

| Mode | Behavior | When to use |
|---|---|---|
| `full_auto` | Bot submits without any pause. | After you've tested + trust your answer bank. |
| `semi_auto` ⭐ | Bot pauses (closes modal) on any **unknown screener question**. Question is added to the dashboard for you to answer; next time bot reuses it. | **Recommended default.** |
| `safe_auto` | Bot pauses in the **terminal** before clicking Submit — you press ENTER to confirm. | First runs, important accounts. |

---

## 🌐 Web Dashboard

Visit `http://localhost:5050`:

- **Dashboard**: stats, live logs, pause/resume controls, unanswered queue
- **Applications**: filterable history of every job (applied / skipped / failed)
- **Application detail**: full Q&A trail for each job
- **Questions**: edit your answer bank, resolve unanswered questions

---

## 🧠 How It Works (One Slide)

```
config.yaml ──┐
              ├──► CandidateProfile ──┐
.env ─────────┤                       │
              ├──► LinkedInExtractor ─┤
answers.json ─┘                       ├──► Orchestrator
                                      │       │
        ┌──── BaseExtractor ────┐     │       ▼
        │ login() / search() /  │     │   SQLite
        │ collect_job_cards() / │     │       │
        │ open_job_detail() /   │     │       ▼
        │ apply()               │     │   Flask UI
        └───────────────────────┘     │
                                      │
                Drop a new file ──────┘
                here for Indeed,
                Glassdoor, etc.
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the deep dive.

---

## 🔌 Adding a New Platform

See [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md). TL;DR:

```python
# packages/extractors/indeed.py
from packages.extractors.base import BaseExtractor

class IndeedExtractor(BaseExtractor):
    name = "indeed"
    base_url = "https://www.indeed.com"

    def login(self, email, password, totp_secret=""): ...
    def search(self, filters): ...
    def collect_job_cards(self, max_cards=50): ...
    def open_job_detail(self, card): ...
    def can_auto_apply(self, job): ...
    def apply(self, job, resume_path, mode="semi_auto"): ...
```

Then register in `apps/worker/runner.py`:

```python
EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
    "indeed": IndeedExtractor,    # ← new
}
```

Zero changes to the orchestrator, filters, storage, or UI.

---

## 📁 Project Structure

```
job-hunter-pro/
├── config.yaml              # All your preferences
├── .env / .env.example      # Secrets
├── data/
│   ├── applications.db      # SQLite (auto-created)
│   ├── answers.json         # Answer bank
│   ├── unanswered.json      # Queue of new questions
│   └── logs/bot.log         # Rotating log file
├── resumes/
│   └── base_resume.pdf      # Put your resume here
├── packages/
│   ├── core/                # Models, exceptions, filters
│   ├── extractors/
│   │   ├── base.py          # Abstract BaseExtractor
│   │   └── linkedin.py      # LinkedIn implementation
│   ├── stealth/             # Browser + humanizer
│   └── storage/             # DB + answer bank
├── apps/
│   ├── worker/runner.py     # Orchestrator
│   ├── worker/control.py    # Pause/Resume/Stop
│   └── web/app.py           # Flask dashboard
├── docs/                    # ARCHITECTURE, PLUGIN_GUIDE, ROADMAP, TROUBLESHOOTING
└── docker-compose.yml
```

---

## 📚 Documentation Index

| Doc | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design + data flow |
| [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) | How to add Indeed/Glassdoor/JobStreet |
| [docs/SETUP.md](docs/SETUP.md) | Step-by-step install (Win/Mac/Linux/Docker) |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors + fixes |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phase 2 → Phase 5 plan |

---

## 🛡️ Privacy

- 100% local — no telemetry, no analytics
- Credentials only in `.env` and the Docker volume `chrome-profile`
- Database is plain SQLite — back it up however you like
- OpenAI API (Phase 2) is the only outbound call, and only if you enable it
