# 👨‍💻 Development Guide

## Dev Setup
```bash
git clone https://gitlab.com/1bulan1m/job-hunter-pro.git
cd job-hunter-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # fill values
python run_web.py
```

## Code Organization
See [00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md) and [02_ARCHITECTURE.md](02_ARCHITECTURE.md).

| Add this | Where |
|---|---|
| AI feature | packages/ai/ |
| New platform | packages/extractors/<name>.py |
| New page | apps/web/templates/ + app.py |
| New filter | packages/core/filters.py |
| DB column | packages/storage/db.py |
| Prompt | docs/08_PROMPTS_LIBRARY.md |

## Code Style
- PEP 8
- Type hints helpful (full P5)
- Docstrings for public methods
- f-strings
- Loguru with emoji prefix:
  - ✅ Success, ❌ Error, ⚠️ Warning
  - 🤖 AI, 💾 Persistence, 📋 Progress
  - 🛡️ Security, 🔍 Search, 📸 Screenshot

## Adding a Feature
1. Read [00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md)
2. Find phase in [12_PHASE_ROADMAP.md](12_PHASE_ROADMAP.md)
3. Read PRD in [PRDs/](PRDs/)
4. Implement following pattern
5. Update [17_CHANGELOG.md](17_CHANGELOG.md), [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
6. Test manually
7. Package as `patch/job-hunter-pro-patchN/`

## Debug
1. `HEADLESS=false` see browser
2. Check `data/logs/bot.log`
3. Check `data/screenshots/`
4. Add `logger.debug(...)`
5. `LOG_LEVEL=DEBUG` in `.env`
6. Inspect DOM in DevTools

## VSCode workflow
See [VSCODE_GUIDE.md](VSCODE_GUIDE.md).

## Git workflow
See [GITLAB_INTEGRATION.md](GITLAB_INTEGRATION.md).
