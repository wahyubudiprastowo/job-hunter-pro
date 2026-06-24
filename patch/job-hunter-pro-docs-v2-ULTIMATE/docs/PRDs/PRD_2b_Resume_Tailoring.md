# PRD: Phase 2b — AI Resume Tailoring

## 0. Status
| Field | Value |
|---|---|
| Phase | 2b |
| Status | 🟡 PARTIAL (code in repo, counter=0 in last run) |
| Patch | Patch 8 (external, undocumented) |
| Source code | `packages/ai/resume_tailor.py` (assumed) |
| Acceptance | Unknown — need code review |

## 1. Problem Statement
Generic resume yields ~5% LinkedIn response rate. ATS scanners filter by keyword match. Recruiters scan resumes in 6 seconds — needs upfront relevance.

## 2. User Story
As a candidate, for each Easy Apply job, I want a custom-tailored resume that emphasizes matching skills WITHOUT inventing experience, so my application bypasses ATS filters and catches recruiter's eye.

## 3. Goals & Non-Goals
### Goals
- ✅ Tailor resume per job
- ✅ ATS-friendly format
- ✅ Cache to avoid regen
- ❌ NOT inventing experience (strict)
- ❌ NOT exceeding 1 page

### Acceptance gates (from doc/12 Phase 2b)
- Diff has NO new technology names
- Word count ≤ 1.1 × base
- PDF renders cleanly
- Tested on 3 different JDs

## 4. Tech Spec
### Files (expected)
- `packages/ai/resume_tailor.py` (new)
- `packages/stealth/browser.py` (modified — faster startup)
- `apps/worker/runner.py` (modified — integration)
- `config.yaml` (new keys)

### Config
```yaml
ai:
  resume_tailoring: true
  resume_output_dir: "resumes/generated"
```

### Pipeline
```
Job JD → AI prompt (resume.v1) + CV text + JD
       → JSON: {summary, highlighted_skills, experience_bullets, key_tools}
       → reportlab → PDF
       → resumes/generated/{Company}_{Title}_{JobID}.pdf
       → upload in apply()
```

### Dependencies
- `reportlab>=4.2.5`
- `pdfminer.six` (parse base CV PDF) OR plain `resumes/base_resume.txt`

## 5. Step-by-Step Implementation
1. Read [08_PROMPTS_LIBRARY.md](../08_PROMPTS_LIBRARY.md) `resume.v1`
2. Parse base CV (PDF text extract OR plain .txt)
3. AI call with system prompt + CV + JD
4. Parse AI JSON response
5. **Validate**: no new tech (anti-hallucination Layer 6)
6. **Validate**: word count ≤ 1.1× base
7. Render PDF via reportlab
8. Cache to `resumes/generated/`
9. In `apply()`: upload tailored instead of base
10. On any error → fallback to base CV

## 6. Anti-Hallucination Guards
- ✅ Layer 1: System prompt forbids invention
- ✅ Layer 6: `detect_new_tech()` diff validator
- ✅ Layer 8: First 3 generations require manual review
- ✅ Fallback: use base CV on validation failure

## 7. Implementation Checklist
### Build
- [ ] `resume_tailor.py` exists (verify in production)
- [ ] CV parser handles PDF input
- [ ] AI integration with `resume.v1`
- [ ] JSON response parser
- [ ] Anti-hallucination validator
- [ ] reportlab PDF renderer
- [ ] Cache mechanism
- [ ] Integration in `apply()`
- [ ] config.yaml: `ai.resume_tailoring` flag
- [ ] Fallback to base CV on error

### Verify (currently 🟡 unknown — counter=0)
- [ ] Generated PDF differs from base
- [ ] Diff contains NO new tech names
- [ ] Word count ≤ 1.1 × base
- [ ] PDF renders without garbled chars
- [ ] Test on 3 different JDs
- [ ] Tailored uploaded, not base

### Document
- [ ] Patch 8 actual content captured in PATCH_HISTORY_LEDGER.md
- [ ] This PRD updated to ✅ DONE after verification

## 8. Acceptance Tests
- [ ] Run bot → log shows `🎨 Resume tailoring ENABLED`
- [ ] Log shows `📄 Generated tailored resume: <path>`
- [ ] Counter `tailored: N` where N > 0
- [ ] Open generated PDF — content matches base CV facts only
- [ ] Re-run same job — log shows `📄 Reusing cached tailored resume`

## 9. Log Patterns (per PATCH 8 notes)
```
SUCCESS | 📄 Loaded CV: 6023 chars
SUCCESS | 🎨 Resume tailoring ENABLED
SUCCESS | 📄 Generated tailored resume: resumes/generated/<Company>_<Title>_<JobID>.pdf
INFO    | 📄 Reusing cached tailored resume: <path>
SUCCESS | ✅ APPLIED (tailored) [<Title> @ <Company>]
INFO    | Run done. Counters: {'applied': 9, 'tailored': 9, ...}
```

## 10. Risks
| Risk | Mitigation |
|---|---|
| AI invents tech | Layer 6 detect_new_tech() rejects |
| Invalid JSON | Fallback to base CV |
| AI cooldown mid-run | Fallback to base CV for remaining jobs |
| Slow tailoring (>20s) | AI timeout → fallback |
| PDF render fail | Try/except → fallback to base |

## 11. Why counter=0 in current run?
Possibilities:
1. `ai.resume_tailoring: false` in current `config.yaml`
2. `base_resume.txt` not present (parser failed)
3. AI cooldown active
4. All resumes rejected by validator (CHECK LOGS)

### Diagnosis
```powershell
# Check config
Get-Content config.yaml | Select-String "resume_tailoring"

# Check resume exists
Get-ChildItem resumes\base_resume.*

# Check generated dir
Get-ChildItem resumes\generated -ErrorAction SilentlyContinue

# Check logs
Get-Content data\logs\bot.log | Select-String "tailored|tailor|🎨"
```

## 12. Cross-Refs
- [08_PROMPTS_LIBRARY.md](../08_PROMPTS_LIBRARY.md) `resume.v1`
- [20_ANTI_HALLUCINATION.md](../20_ANTI_HALLUCINATION.md) Layer 6
- [12_PHASE_ROADMAP.md](../12_PHASE_ROADMAP.md) Phase 2b
