# 🛟 Troubleshooting

## Setup & Build

### rapidfuzz fails (Python 3.13)
Use `rapidfuzz>=3.10.1` in requirements.

### Docker build fails libgdk-pixbuf2.0-0
Use `python:3.11-slim-bookworm` + `libgdk-pixbuf-2.0-0` (with dash).

### PowerShell emoji mojibake
Use `.cmd` batch files instead of `.ps1`.

### Set-ExecutionPolicy blocked
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

## Browser & Login

### "Login timed out"
- 2FA pending. Set `HEADLESS=false`, solve manually.
- Or set `LINKEDIN_TOTP_SECRET`.

### Chrome version mismatch
- Update Chrome, set `CHROME_VERSION_MAIN=126`.

### "session is dead"
- Chrome crashed. Add `shm_size: 4g`.

## Bot Behavior

### "Submit clicked but no confirmation"
- Check `data/screenshots/verify_failed_*.png`.
- Patch 1+ added 9 multi-language indicators.

### Stuck at X% progress
- Auto-aborts after 2x same progress.
- Check `data/screenshots/stuck_*.png`.

### Unanswered questions piling up
- Enable AI: `ai.enabled: true`, `ai.question_fallback: true`.
- Set `AI_API_KEY` in `.env`.

### Italian/German form not progressing
- Patch 2 added multi-lang buttons. Verify applied.

## AI Issues

### AI not called
- Check log for "AI provider ready"
- Verify config + .env

### Cooldown stuck
- Wait 5 min OR restart bot
- Test endpoint with curl

### Resume tailoring `tailored: 0`
- Check `ai.resume_tailoring: true`
- Check `resumes/base_resume.txt` exists
- Check logs for tailor errors
- See [PRDs/PRD_2b_Resume_Tailoring.md](PRDs/PRD_2b_Resume_Tailoring.md) section "Why counter=0"

## Worker / Heartbeat

### "Is zombie: Yes"
- Worker stuck/dead. Click "Reset State".
- Restart bot.

### Heartbeat too old
- Reset State button.
- Check `data/.control/heartbeat.txt`.

## LinkedIn

### "Account restricted"
- STOP. Wait 24-48h.
- Solve challenges manually.
- Resume with reduced caps.

### No Easy Apply jobs
- Verify URL has `f_AL=true`.
- Try different location.

## Folder

### Patch from patch/ folder
Drop ZIP in `patch/`, extract, `apply.cmd` from inside extracted folder.

### Backups
Auto-created `.backup_pN_<ts>/`. Rollback via copy.

## 🔗 Per-patch fixes in [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
