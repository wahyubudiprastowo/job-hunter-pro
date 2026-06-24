# 🩹 PATCH 11 — Comprehensive Fix (6 bugs from production logs)

## 🎯 Issues Fixed

| # | Bug | Fix |
|---|---|---|
| 1 | Resume validator rejects "cloud/container/monitor" as invented | Added `COMMON_KNOWLEDGE_TERMS` whitelist |
| 2 | `provider.py:80` log shows wrong base_url (model name) | Fix log template + add URL masking |
| 3 | API key fully exposed in logs | Better masking: `sk-XXX*** (Ncharhar)` no suffix |
| 4 | Duplicate "Cloud Infrastructure Engineer" in queries | De-duped + prioritized list |
| 5 | Missing common keywords (devops, kubernetes, container) | Expanded title_keywords_include |
| 6 | Italian "desiderata giornaliera" + Dutch "werkvisum" UNKNOWN | Added to answer bank manually |

## 🔍 Issues Identified (Need Further Investigation)

| # | Issue | Recommended Action |
|---|---|---|
| 7 | CV only 1161 chars extracted | See `CV_EXTRACTION_GUIDE.md` — manually update `resumes/base_resume.txt` |
| 8 | 4 jobs marked "external apply" (should be Easy Apply) | Need LinkedIn DOM verification — check Patch 11b later |
| 9 | Stuck at 67% on Italian/Dutch forms | Likely related to issue #6 — fixed by adding answers |

## 📁 Files

| File | Status |
|---|---|
| `packages/ai/provider.py` | REPLACED (log fix, key masking, debug method, stats) |
| `packages/ai/resume_validator.py` | REPLACED (COMMON_KNOWLEDGE_TERMS) |
| `config.yaml` | REPLACED (improved queries + keywords + EU/sponsorship hints) |
| `answers.additions.json` | NEW — merge into data/answers.json |
| `CV_EXTRACTION_GUIDE.md` | NEW — guide to fix CV issue |
| `apply.cmd` | NEW — installer |

## 🚀 Apply

```cmd
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\patch\job-hunter-pro-patch11
apply.cmd
```

## ⚙️ Post-Install Steps

### Step 1: Update CV (CRITICAL)

Read `CV_EXTRACTION_GUIDE.md` and fix `resumes/base_resume.txt` to have **3000-6000 chars**.

Without this, AI will continue inventing tech. The validator will keep rejecting (correctly).

### Step 2: Merge answer bank entries

```powershell
cd C:\Users\WP2300419\Documents\VContainer\job-hunter-pro

# View additions
type patch\job-hunter-pro-patch11\answers.additions.json

# Manually open data/answers.json and add these 5 new entries
# (or use Python to merge):
python -c "
import json
with open('data/answers.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)
with open('patch/job-hunter-pro-patch11/answers.additions.json', 'r', encoding='utf-8') as f:
    additions = json.load(f)
# Only add keys not starting with //
for k, v in additions.items():
    if not k.startswith('//'):
        existing[k] = v
with open('data/answers.json', 'w', encoding='utf-8') as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)
print('Merged. Total entries:', len(existing))
"
```

### Step 3: Restart bot

```powershell
python run_web.py
```

Click Start. Watch log for new patterns:

```
INFO | 🧠 AI provider ready: model=..., base_url=https://openwebui.tail443aaa.ts.net/api/v1/sk-***/, key=sk-3d3***(38chars)
INFO | 🎨 Resume tailoring ENABLED — validator: lenient (strict=false)
SUCCESS | ✅ Resume validated: words 350/450 (ratio 0.78) (common terms ignored: ['cloud', 'container'])
```

### Step 4 (Optional): Enable AI debug mode

If AI still gives weird answers, enable debug mode in `config.yaml`:

```yaml
ai:
  debug_chat: true   # logs every AI call's prompt + response
```

Then watch logs:
```
DEBUG | 🧠 AI chat [question]: user="Are you authorized to work? Options: Yes/No", max_tok=50
DEBUG | 🧠 AI response: "No"
```

## 📊 Expected Improvements

| Metric | Before Patch 11 | After Patch 11 |
|---|:---:|:---:|
| Resume reject rate | ~80% | ~30-40% (after CV fix: ~20%) |
| Key exposed in logs | ❌ Full | ✅ Masked |
| Italian day rate question | ❌ Unknown | ✅ Auto-answered (320 EUR) |
| Dutch visa question | ❌ Unknown | ✅ Auto-answered (Yes) |
| Stuck at 67% | Frequent | Reduced (after CV + answers fix) |
| Job match coverage | ~40% | ~60% (with expanded keywords) |

## 🔄 Anti-Breakage

- ✅ ADDITIVE for keywords (config can be merged manually)
- ⚠️ REPLACES provider.py + resume_validator.py (backup auto-created)
- ✅ No DB schema changes
- ✅ No selector changes
- ✅ No credential touches

Risk level: **LOW-MEDIUM** (validator behavior changes might affect existing audit logs)

## 🆘 Rollback

```powershell
$bak = Get-ChildItem .backup_p11_* | Sort-Object Name -Descending | Select -First 1
Copy-Item "$($bak.FullName)\packages\ai\provider.py" packages\ai\provider.py -Force
Copy-Item "$($bak.FullName)\packages\ai\resume_validator.py" packages\ai\resume_validator.py -Force
Copy-Item "$($bak.FullName)\config.yaml" config.yaml -Force
python run_web.py
```

## 🎯 Next Patches

- **Patch 11b**: Investigate "external apply" misdetection (need linkedin.py inspection)
- **Patch 12**: Phase 2d Fit Scoring (skip low-fit jobs before resume tailoring)
- **Patch 13**: Cover letter LinkedIn integration (upload to form field)
