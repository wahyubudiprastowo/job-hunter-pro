# 🩹 PATCH 10 — Phase 2c: Cover Letter Generator

## 🎯 What This Does

For each Easy Apply job with a JD, generates a tailored ~250-word cover letter that:
- References company name (mandatory)
- References at least 1 specific JD detail (proves AI read JD)
- Uses only candidate's real CV experience
- Auto-detects job language (EN/IT/ES/FR/DE/NL/PT) for localized salutation
- Caches by `{Company}_{JobID}` to avoid regen

Output: `cover_letters/generated/{Company}_{JobID}.txt` + `.pdf`

## 🛡️ Anti-Hallucination Guards (7 checks)

| Check | Threshold | Outcome |
|---|---|---|
| Word count | 150-350 (target 250) | Reject if outside |
| Company name | Must be referenced | Reject if missing |
| JD-specific detail | ≥ 1 meaningful word from JD in letter | Reject if 0 |
| Acceptable salutation | Multi-language list | Reject if generic opener |
| Forbidden phrases | 11 buzzwords/clichés | Reject in strict mode |
| Tech cross-reference | Use VARIANT_TO_CANONICAL from resume_validator | Reject if invents |
| Years inflation | Claimed ≤ 1.5 × candidate's actual | Reject if inflated |

## 📁 Files

| File | Status |
|---|---|
| `packages/ai/cover_letter.py` | NEW |
| `packages/ai/cover_letter_validator.py` | NEW |
| `apps/worker/runner.py` | **MANUAL EDIT** (see RUNNER_EDIT_INSTRUCTIONS.txt) |
| `config.yaml` | **MANUAL EDIT** (add 3 ai. keys) |
| `cover_letters/generated/` | NEW directory |

## ⚠️ Honest Limitations of This Patch

**1. LinkedIn integration NOT included (yet)**
Cover letters are generated and saved to disk but NOT yet uploaded into LinkedIn
Easy Apply cover letter field. That's a separate concern requiring extractor
modifications. Coming in **Patch 10b** (linkedin.py extension).

For now, you can:
- View generated letters in `cover_letters/generated/`
- Manually copy-paste if a job has the field
- Or wait for Patch 10b for automation

**2. Language detection is heuristic**
Uses keyword frequency. May misclassify if JD is bilingual or contains few
language-specific words. Falls back to English.

**3. Validator is intentionally strict**
You may see high reject rate initially. Set `cover_letter_strict: false` in
config to allow up to 1 new tech mention (still rejects on missing company etc).

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch10
apply.cmd
```

## ✅ Verification

### Step 1: Self-test
```powershell
python patch\job-hunter-pro-patch10\test_cover_letter.py
```

Expected:
```
=== TEST: Good English letter ===
✅ PASS — expected valid=True, got valid=True

=== TEST: Rejects generic opener + buzzwords ===
✅ PASS — expected valid=False, got valid=False

=== TEST: Rejects missing company name ===
✅ PASS

=== TEST: Rejects invented tech ===
✅ PASS

=== TEST: Rejects too short ===
✅ PASS

=== TEST: Rejects too long ===
✅ PASS

=== TEST: Valid Italian letter ===
✅ PASS

RESULTS: 7/7 tests passed
```

### Step 2: Apply runner.py edits (6 sections)
Follow RUNNER_EDIT_INSTRUCTIONS.txt.

### Step 3: Enable in config.yaml
Add to `ai:` block:
```yaml
ai:
  cover_letter: true
  cover_letter_strict: true
  cover_letter_output_dir: "cover_letters/generated"
```

### Step 4: Run bot
```powershell
python run_web.py
```

Watch for logs:
```
INFO | 💌 Cover letter generation ENABLED
INFO | 💌 Generated cover letter: cover_letters/generated/SORINT_4438923.txt
INFO | 💌 Cover letter validated [job=4438923]: 248 words, company=✓, jd_ref=✓
...
INFO | 💌 Cover letters: 12 generated, 3 rejected (20% reject rate)
INFO | 🎉 Run done. Counters: {'applied': 15, 'tailored': 12, 'cover_letters': 12, ...}
```

## 📊 Expected Behavior

- Most jobs without cover letter field: bot still applies normally (resume only)
- Jobs WITH cover letter field: not yet uploaded (Patch 10b)
- Generated letters reviewable in `cover_letters/generated/` (txt + pdf)
- Failed validations saved as `<key>.rejected.json` for debugging

## 🐛 Known Bugs Carried Over

From `provider.py` (Patch 5-8): log line shows wrong `base_url` value (shows
model name instead of URL). Will be addressed in Patch 11 along with secure
key logging.

## 🔄 Anti-Breakage

Per docs/ANTI_BREAKAGE_RULES.md:
- ✅ ADDITIVE — all new files, no replacements
- ✅ Backward compatible — bot works fine without cover letter
- ✅ Graceful fallback — generation failure → no upload, continue
- ✅ Reuses VARIANT_TO_CANONICAL from resume_validator (no duplication)
- ✅ No selector changes
- ✅ No DB schema changes
- ✅ No credential touches

Risk level: **LOW** ✅

## 🆘 Rollback

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro
Remove-Item packages\ai\cover_letter.py
Remove-Item packages\ai\cover_letter_validator.py
# Revert runner.py manually (remove EDIT 1-6 additions)
# Set ai.cover_letter: false in config.yaml
```

## 📝 Documentation Updates Needed

After applying:
- `docs/17_CHANGELOG.md` — add Patch 10 entry
- `docs/PATCH_HISTORY_LEDGER.md` — Patch 10 DOCUMENTED
- `docs/PRDs/PRD_2c_Cover_Letter.md` — status PARTIAL (generation done, upload pending)

## 🎯 Next Patches

- **Patch 10b**: Extractor integration — upload cover letter to LinkedIn field if present
- **Patch 11**: Fix `provider.py:80` log bug + better key masking
- **Patch 12**: Phase 2d Fit Scoring
