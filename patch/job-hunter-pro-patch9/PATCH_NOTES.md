# 🩹 PATCH 9 — Anti-Hallucination Validator for Resume Tailoring

## 🎯 Why This Patch

Per docs/20_ANTI_HALLUCINATION.md, **Layer 6 (Diff Verification)** was MISSING
from Patch 8's `resume_tailor.py`. AI could invent tech/skills without detection.

This patch adds the validator that **rejects hallucinated resumes** and
automatically falls back to base CV.

## 🛡️ What It Checks

| Check | Method | Outcome on fail |
|---|---|---|
| **New tech detection** | Compare 200+ tech terms between base CV & AI output | Reject |
| **Word count inflation** | Tailored ≤ 1.1 × base words | Reject |
| **Missing JSON keys** | All 4 required keys present | Reject (early bail) |
| **Years inflation** | Claimed years ≤ 1.5 × candidate's actual | Reject |
| **Forbidden phrases** | Buzzwords ("revolutionary", "led 100+") | Reject |

Tech database covers: Cloud, Containers, IaC, CI/CD, Monitoring, Databases,
Messaging, Languages, Web Frameworks, ML/AI, Security, Networking, Storage,
Linux, Virtualization, Certifications.

## 📁 Files

| File | Type | Purpose |
|---|---|---|
| `packages/ai/resume_validator.py` | **NEW** | Validator module + 200+ tech terms DB |
| `packages/ai/resume_tailor.py` | **REPLACED** | Integrated validator call + safe-format fix |
| `apps/worker/runner.py` | **MANUAL EDIT** | See `RUNNER_EDIT_INSTRUCTIONS.txt` |
| `config.snippet.yaml` | Reference | Add `validator_strict: true` to ai: |
| `test_validator.py` | Self-test | Run to verify all 6 test cases pass |

## 🐛 Bonus Fixes

- **Latent `.format()` bug**: when CV contains `{` or `}`, `_safe_format()` now
  handles it gracefully (returns None instead of crash).
- **Audit trail**: rejected JSONs saved to `resumes/generated/<key>.rejected.json`
  for debugging — see exactly what AI invented.

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch9
apply.cmd
```

The installer:
1. Backups existing files to `.backup_p9_<timestamp>/`
2. Copies new `resume_validator.py`
3. Replaces `resume_tailor.py`
4. **PROMPTS YOU** to manually edit `runner.py` (3 small edits, instructions in `RUNNER_EDIT_INSTRUCTIONS.txt`)
5. Reminds to add `validator_strict: true` to `config.yaml`

## ✅ Verification

### Step 1: Run self-test
```powershell
python patch\job-hunter-pro-patch9\test_validator.py
```

Expected output:
```
=== TEST: Valid resume (existing tech only) ===
✅ PASS — expected valid=True, got valid=True

=== TEST: Rejects AWS hallucination ===
✅ PASS — expected valid=False, got valid=False
   Reasons: ['AI invented 3 new tech: aws, cloudformation, lambda']

... 4 more passes ...

==================================================
RESULTS: 6/6 tests passed
✅ All tests PASSED — validator works correctly
```

### Step 2: Apply manual edits to runner.py
Open `apps/worker/runner.py` and apply 3 edits from `RUNNER_EDIT_INSTRUCTIONS.txt`.

### Step 3: Update config.yaml
Add to `ai:` block:
```yaml
ai:
  validator_strict: true
```

### Step 4: Test in real run
```powershell
python run_web.py
# Click Start
# Watch logs for:
#   ✅ Resume validated [job=...] — words 350/400 (ratio 0.88)
#   🛑 Resume REJECTED [job=...] — AI invented 2 new tech: aws, lambda
```

## 📊 Expected Counter Behavior

Before Patch 9:
```python
counters = {"applied": 5, "skipped": 10, "tailored": 5}
# Includes hallucinated PDFs — unsafe!
```

After Patch 9:
```python
counters = {"applied": 5, "skipped": 10, "tailored": 3, "tailored_rejected": 2}
# tailored: 3 = clean PDFs uploaded
# tailored_rejected: 2 = AI hallucinated, fell back to base CV
```

Log marker:
```
🎨 Tailoring: 3 accepted, 2 rejected (40% reject rate)
🎉 Run done. Counters: {...}
```

If reject rate > 50%, consider:
- Tighten prompt (per docs/08 resume.v1)
- Switch to better model (gpt-4o vs gpt-4o-mini)
- Lower `ai.temperature` (0.2 → 0.1)

## 🔄 Anti-Breakage Guarantee

Per docs/ANTI_BREAKAGE_RULES.md:
- ✅ ADDITIVE — new file `resume_validator.py`
- ✅ Backward compatible — if validator import fails, tailoring still works (just no check)
- ✅ Graceful fallback — rejected resume → base CV used, bot continues
- ✅ No selector changes
- ✅ No DB schema changes
- ✅ No credential touches
- ✅ Existing 18 applies + 121 answers untouched

Risk level: **LOW** ✅

## 🆘 Rollback

If Patch 9 causes issues:
```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
$bak = Get-ChildItem .backup_p9_* -Directory | Sort-Object Name -Descending | Select -First 1
Copy-Item "$($bak.FullName)\packages\ai\resume_tailor.py" packages\ai\resume_tailor.py -Force
Remove-Item packages\ai\resume_validator.py
# Revert runner.py manually (counters & tailored_rejected)
python run_web.py
```

## 📝 Documentation Updates

After applying, also update:
- `docs/17_CHANGELOG.md` — add Patch 9 entry
- `docs/PATCH_HISTORY_LEDGER.md` — Patch 9: DOCUMENTED
- `docs/PRDs/PRD_2b_Resume_Tailoring.md` — Layer 6 ✅ now implemented

## 🎯 What Comes After Patch 9

With anti-hallucination locked, safe to proceed to:
- **Patch 10** — Phase 2c Cover Letter (similar pattern)
- **Patch 11** — Phase 2d Fit Scoring
- **Patch 12** — Move api_key from config.yaml to .env (security hardening)
