# 🚫 Anti-Breakage Rules

> **The bot is in production. 18 real EU job applications submitted. Do not break it.**

These rules are **non-negotiable**. If a patch violates any of these, it must be rolled back.

---

## 🛑 NEVER Touch (without explicit confirmation)

| Asset | Reason | Recovery if broken |
|---|---|---|
| `.chrome-profile/` directory | Contains cached LinkedIn session — loss = re-login + possible 2FA challenge | Re-login manually with `HEADLESS=false` |
| `.env` file in production | Contains real credentials | Restore from password manager |
| `data/applications.db` | Has 18 real applies + 121 saved answers | Restore from `data/applications.db-journal` |
| `data/answers.json` | 121 entries — irreplaceable training data | Restore from `.backup_*` folder |
| Working LinkedIn selectors | If working, don't change | Apply previous patch backup |
| `EXTRACTOR_REGISTRY` order | Bot depends on this dict | Restore from runner.py.bak |

---

## 🛑 NEVER Reduce Acceptance Criteria

If a PRD says "≥ 90% apply success rate", a new patch cannot lower it to 80%.

If a patch's acceptance test fails → fix the patch, don't lower the bar.

---

## 🛑 NEVER Remove Working Logging

The user relies on visual log scanning. Keep:
- ✅ Success indicators
- 🤖 AI activity markers
- 💾 Persistence markers
- 📋 Progress indicators
- ⚠️ Warnings
- ❌ Errors
- 🚧 Stuck detection
- 📸 Screenshot markers

---

## 🛑 NEVER Hard-Code Secrets

Even in dev:
- ❌ `api_key: "sk-abc..."` in config.yaml
- ✅ `api_key: ""` in config.yaml + `AI_API_KEY=sk-...` in .env

---

## 🛑 NEVER Edit Files In-Place During Development

Always:
1. Create patch folder `patch/job-hunter-pro-patchN/`
2. Place modified files there
3. Use `apply.cmd` to install (auto-backup)
4. Verify
5. Commit backups + patched files to GitLab

This way **any change is reversible**.

---

## ✅ ALWAYS Do These

### Before any code change
- [ ] Read the actual current code in the file you'll modify
- [ ] Check `docs/PATCH_HISTORY_LEDGER.md` for prior context
- [ ] Check `docs/CURRENT_STATE_SNAPSHOT.md` for production state
- [ ] Verify the relevant PRD acceptance criteria

### During code change
- [ ] Centralize selectors in module-level `SELECTORS` dict
- [ ] Add logging with emoji prefix
- [ ] Handle exceptions gracefully (never crash bot)
- [ ] Maintain backward compatibility with existing data
- [ ] Add new config keys with sensible defaults

### After code change
- [ ] Manual smoke test on throwaway account
- [ ] Verify all checklist items in PRD
- [ ] Update `docs/17_CHANGELOG.md`
- [ ] Update `docs/PATCH_HISTORY_LEDGER.md`
- [ ] Commit + push to GitLab
- [ ] Backup ZIP of `patch/job-hunter-pro-patchN/`

---

## 🛡️ Specific Anti-Breakage for Each Component

### LinkedIn Extractor
- ❌ Don't remove multi-language button labels — EU jobs need them
- ❌ Don't change Easy Apply button XPath without testing on 5 jobs
- ❌ Don't disable diversity auto-decline (it prevents NEEDS_ANSWERS spam)
- ❌ Don't increase apply rate above existing caps (account suspension risk)
- ✅ Do add new selectors as **additions** to existing dict, never replacements

### AI Layer
- ❌ Don't remove "UNKNOWN" escape hatch from prompts
- ❌ Don't remove fuzzy validation on multi-choice answers
- ❌ Don't remove cooldown mechanism
- ❌ Don't disable `auto_save_answers` — kills learning
- ✅ Do version new prompts (`resume.v1` → `resume.v2`)

### Question Bank (121 entries currently)
- ❌ Don't bulk-edit or rewrite the file
- ❌ Don't lowercase or normalize all keys (breaks fuzzy match cache)
- ✅ Do add new entries via UI or via bot's auto-save

### Control Plane
- ❌ Don't change file paths in `data/.control/`
- ❌ Don't remove the heartbeat mechanism (newer Patch 6-7)
- ❌ Don't remove zombie detection
- ✅ Do add new control commands as additions

### Resume Tailoring (Phase 2b)
- ❌ Don't disable anti-hallucination validator
- ❌ Don't allow new tech terms in diff
- ❌ Don't exceed 1.1× base word count
- ✅ Do fallback to base resume on any error

---

## 📋 Risk Assessment Template (for any new patch)

Before applying patch N, fill this:

```
Patch N — Risk Assessment

Touches files: [list]
Touches selectors: [yes/no — which ones?]
Touches working features: [list features at risk]
Touches AI prompts: [yes/no — versioned?]
Touches data files: [yes/no — backup created?]
Touches credentials: [yes/no — secrets isolated?]

Risk level: [LOW / MEDIUM / HIGH]

Rollback plan:
1. ...
2. ...

If HIGH risk: test on throwaway account first, get explicit OK.
```

---

## 🆘 Emergency Rollback

If a patch breaks production:

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro

# Find latest backup
$latestBackup = Get-ChildItem .backup_* -Directory | Sort-Object Name -Descending | Select-Object -First 1
Write-Host "Latest backup: $($latestBackup.Name)"

# Restore all files
Get-ChildItem $latestBackup -Recurse -File | ForEach-Object {
    $relativePath = $_.FullName.Substring($latestBackup.FullName.Length + 1)
    $destPath = Join-Path $PWD $relativePath
    Copy-Item $_.FullName $destPath -Force
    Write-Host "Restored: $relativePath"
}

# Verify
git status

# Restart bot
python run_web.py
```

---

## 🔗 Related
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
- [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
- [16_TROUBLESHOOTING.md](16_TROUBLESHOOTING.md)
- [20_ANTI_HALLUCINATION.md](20_ANTI_HALLUCINATION.md)
