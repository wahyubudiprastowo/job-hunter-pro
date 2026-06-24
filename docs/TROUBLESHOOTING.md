# 🛟 Troubleshooting

## "Login timed out"
- LinkedIn requires 2FA or CAPTCHA. Set `HEADLESS=false`, solve manually.
- If you have an authenticator app, fill `LINKEDIN_TOTP_SECRET=` in `.env`
- The session is then cached in `.chrome-profile/` — no need to re-login next time.

## "selector_miss" / "Modal not found"
- LinkedIn updated their DOM. Open `packages/extractors/linkedin.py` → `SELECTORS = {...}`
- Open Chrome DevTools, find the new class name / xpath, update.
- Submit a PR or just keep it patched locally.

## Chrome version mismatch
- `undetected-chromedriver` auto-downloads a matching driver.
- If it fails: update Chrome, set `CHROME_VERSION_MAIN=126` (your Chrome major version) in `.env`.
- Check your Chrome version: chrome → ⋮ → Help → About Google Chrome.

## Bot applied to 0 jobs but logs look fine
- Check **Applications** page — likely everything was filtered. Loosen `title_keywords_include` or `description_keywords_exclude`.
- Check `data/logs/bot.log` for "SKIP" reasons.

## "No Easy Apply button" for everything
- LinkedIn shows different jobs by region. Verify your search has `easy_apply_only: true` actually filters to Easy Apply.
- Check the URL it navigated to has `f_AL=true` — if not, filter param is wrong.

## Docker container crashes immediately
- Check `docker compose logs jobhunter`. Most common: `.env` missing or `config.yaml` syntax error.
- Validate YAML: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`

## "session is dead" mid-run
- Chrome crashed (low memory). Set `shm_size: "4g"` in `docker-compose.yml`.
- Reduce `max_apply_per_run` if you're on limited RAM.

## Got LinkedIn warning / temporary restriction
- **Stop immediately.** Wait 24-48 hours.
- Reduce `total_apply_per_run` to 5-10.
- Increase `pause_seconds` to 120+.
- Don't run more than 2x per day.

## Web UI shows "(no logs yet)"
- The bot hasn't run yet. Click **🚀 Start**.
- Or check `data/logs/bot.log` is being created (file permissions issue?).

## Pause button doesn't work
- It's polled between jobs — wait up to 30s for it to take effect.
- The current job will finish before pause kicks in.
