# 🦊 GitLab Integration

## Repository
**Canonical**: https://gitlab.com/1bulan1m/job-hunter-pro

This is the **source of truth**. If a doc bundle conflicts with the repo, the repo wins.

---

## 🔄 Sync Workflow

### Pulling latest
```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
git pull origin main
```

### Pushing changes
```powershell
git status
git add <files>
git commit -m "patch N: <description>"
git push origin main
```

### Branch strategy (recommended for future)
```
main           ← production state (deploy-able)
develop        ← integration of patches
patch/N-...    ← per-patch feature branch
```

---

## 📦 Patch Commits

When applying a patch, commit in this order:

```powershell
# 1. Stash any local
git stash

# 2. Pull latest
git pull origin main

# 3. Pop stash
git stash pop

# 4. Apply patch via apply.cmd

# 5. Verify works (run bot, smoke test)

# 6. Commit
git add patch/job-hunter-pro-patchN/
git add docs/
git add <modified-files>
git commit -m "patch N: <semantic description>

- Add: <new files>
- Modify: <changed files>
- Docs: 17_CHANGELOG, PATCH_HISTORY_LEDGER updated

Phase: <X>
Acceptance: <N/M criteria met>"

# 7. Push
git push origin main
```

---

## 🛡️ .gitignore (critical entries)

Make sure your `.gitignore` includes:
```
.env
.venv/
__pycache__/
*.pyc
.chrome-profile/
data/applications.db
data/applications.db-journal
data/logs/*
data/screenshots/*
data/.control/
.backup_*/
resumes/generated/*
cover_letters/generated/*
*.bak
```

**NEVER COMMIT**:
- `.env` (credentials)
- `.chrome-profile/` (LinkedIn session)
- `data/applications.db` (PII)
- Backup folders (large + redundant)

---

## 📜 Commit Message Convention

Format:
```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat:` — new feature
- `fix:` — bug fix
- `patch N:` — applying numbered patch
- `docs:` — documentation only
- `refactor:` — code reorg, no behavior change
- `test:` — test changes
- `chore:` — build/deps

Examples:
```
patch 3: Phase 2a AI Question Fallback

- Add: packages/ai/provider.py, question_bot.py
- Modify: linkedin.py _lookup_answer step 6
- Docs: PRD_2a, CHANGELOG, LEDGER

Phase: 2a
Acceptance: 6/6 ✅
```

---

## 🔍 GitLab CI/CD (Phase 5)

`.gitlab-ci.yml` will be added in Phase 5. Until then:

### Manual checks before push
```powershell
# Validate YAML
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Compile-check all Python
Get-ChildItem -Recurse -Include "*.py" | ForEach-Object {
    python -m py_compile $_.FullName
}

# Check no secrets in commit
git diff --cached | Select-String -Pattern "sk-|password|api_key=[^\s]+" -CaseSensitive:$false
```

---

## 🏷️ Tagging Releases

When a major milestone hits:
```powershell
git tag -a v0.2.0 -m "Phase 2a stable: 18 applies, 121 saved answers"
git push origin v0.2.0
```

Tag scheme:
- `v0.1.x` — Phase 1 (MVP)
- `v0.2.x` — Phase 2 (AI Pro)
- `v0.3.x` — Phase 3 (Differentiators)
- `v0.4.x` — Phase 4 (Multi-platform)
- `v1.0.0` — Phase 5 (Enterprise — public release)

---

## 🆘 If You Mess Up

### Undo last commit (keep changes)
```powershell
git reset --soft HEAD~1
```

### Undo last commit (discard)
```powershell
git reset --hard HEAD~1
```

### Recover from a bad push
```powershell
git revert HEAD
git push origin main
```

### Get back to a specific tag
```powershell
git checkout v0.1.0
```

---

## 📥 Bringing in External Patches (Patch 4-8 from other source)

If you have patches from another LLM session that aren't documented here:

### Option A: User commits them directly
The patch files exist somewhere → user copies into `patch/job-hunter-pro-patchN/` → commits.

### Option B: Forensic from git log
```powershell
git log --oneline --all -50
git show <commit-hash>
```

Find commits that touched the suspect files. Read diff. Document in `docs/PATCH_HISTORY_LEDGER.md`.

### Option C: Ask user to share
Per [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md), AI assistant should ask user to share Patch 4-8 source code.

## 🔗 Related
- [VSCODE_GUIDE.md](VSCODE_GUIDE.md) — VSCode GitLab integration
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) — Patch tracking
- [18_DEVELOPMENT_GUIDE.md](18_DEVELOPMENT_GUIDE.md) — Dev workflow
