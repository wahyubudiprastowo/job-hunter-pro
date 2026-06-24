# 🩹 PATCH 9.1 — Validator Variant Handling + GitHub Mirror Setup

## 🎯 Fixes from Patch 9.0

### Bug: False positive on "load balancer" vs "load balancing"

**Problem**: Patch 9.0 strict comparison rejected legitimate rephrasing:
- Base CV: "HAProxy **load balancing**"
- Tailored: "HAProxy **load balancer**"
- Validator: ❌ REJECTED (treated as new tech)

**Fix**: Added VARIANT_GROUPS mapping for common DevOps term variants:
- `load balancer ↔ load balancing ↔ load balance ↔ LB`
- `k8s ↔ kubernetes ↔ kube`
- `ci/cd ↔ cicd ↔ ci-cd ↔ continuous integration`
- `iac ↔ infrastructure as code`
- `monitoring ↔ observability`
- `sre ↔ site reliability`
- `containers ↔ containerization`
- `autoscaling ↔ auto-scaling ↔ hpa`
- `gitops ↔ git-ops`
- `microservices ↔ service mesh`

### Improvement: Test data more realistic

Updated `test_validator.py`:
- Base CV now mentions Helm explicitly (Test 1 won't fail on Helm)
- Added Test 7: variant handling (load balancer ↔ load balancing)
- All 7 tests should pass now

## 📁 Files

| File | Change |
|---|---|
| `packages/ai/resume_validator.py` | Added VARIANT_GROUPS + `_canonicalize_terms()` |
| `test_validator.py` | Realistic base CV + new variant test |

## 🚀 Apply

This is a small patch on top of Patch 9:

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch9.1
apply.cmd
```

## ✅ Expected Test Result

```
=== TEST: Valid resume (existing tech only) ===
✅ PASS — expected valid=True, got valid=True

=== TEST: Rejects AWS hallucination ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Rejects years inflation ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Rejects word inflation ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Rejects missing key ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Rejects forbidden buzzwords ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Accepts variants ===
✅ PASS — expected valid=True, got valid=True

RESULTS: 7/7 tests passed
✅ All tests PASSED
```

## 🌐 GitHub Mirror Setup (for future fetches)

Your GitHub username `wahyubudiprastowo` exists, but `job-hunter-pro` repo doesn't exist there yet.
You need to create + push:

```powershell
# 1. Create repo on GitHub (public, no auto-init)
# Go to: https://github.com/new
# Name: job-hunter-pro
# Visibility: PUBLIC (so Copilot can fetch)
# Don't initialize with README/LICENSE/etc

# 2. Add GitHub as additional remote
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
git remote add github https://github.com/wahyubudiprastowo/job-hunter-pro.git

# 3. (CRITICAL) Make sure .env is in .gitignore before pushing!
Get-Content .gitignore | Select-String "\.env"
# If empty, add it:
Add-Content .gitignore "`n.env`n.chrome-profile/`ndata/applications.db`n.backup_*/`n"

# 4. Verify no secrets in commits
git log --all -p | Select-String -Pattern "sk-|password|api_key.*sk" -CaseSensitive:$false | Select-Object -First 5

# 5. Push current code to GitHub
git push github main

# 6. Test public access (from anywhere):
curl https://raw.githubusercontent.com/wahyubudiprastowo/job-hunter-pro/main/README.md
```

### Going forward — Workflow

After mirror setup, your patch development workflow:

```
1. Make changes locally
2. Test
3. git push origin main          # GitLab (private, source of truth)
4. git push github main           # GitHub (public mirror for AI fetching)

When asking Copilot/me for help:
"Lihat https://raw.githubusercontent.com/wahyubudiprastowo/job-hunter-pro/main/packages/ai/resume_tailor.py
 lalu bikin patch X"

I can web_fetch that URL → read code → understand context → patch correctly.
```

### Security checks BEFORE pushing to public GitHub

```powershell
# 1. Verify config.yaml has no hardcoded API key
Select-String -Path "config.yaml" -Pattern "sk-[a-zA-Z0-9-]+" | Format-List

# 2. Verify .env not tracked
git ls-files | Select-String -Pattern "\.env$"

# 3. Check git history for accidental commits
git log --all --diff-filter=A -- .env

# 4. If found leak: rotate keys IMMEDIATELY + use BFG repo cleaner
```

## 🎯 What Next

After 7/7 pass + Patch 9 + 9.1 applied:

1. **Run real bot** with `validator_strict: true`
2. **Watch for `🛑 Resume REJECTED`** in logs — that's anti-hallucination working
3. **Setup GitHub mirror** for future workflow
4. **Consider Patch 10**: Phase 2c Cover Letter
