# PRD: Phase 2c — AI Cover Letter

## 0. Status
| Field | Value |
|---|---|
| Phase | 2c |
| Status | ⏭️ PLANNED |
| Patch | TBD |
| Last updated | 2026-06-24 |

## 1. Problem Statement
Generic cover letters are filtered or ignored. Personalized ones get attention but take 15+ min manually per job.

## 2. User Story
As a candidate, when LinkedIn form provides cover letter field, I want a 250-word personalized letter referencing specific JD details and matching my real experience.

## 3. Goals & Non-Goals
### Goals
- ✅ ≤ 300 words
- ✅ References specific JD detail (proves AI read JD)
- ✅ Uses only real experience from resume
- ✅ Localized to job's language
### Non-Goals
- ❌ Claim skills not in resume
- ❌ Generic openers ("I am writing to apply")
- ❌ Address by name unless extractable

## 4. Tech Spec
- `packages/ai/cover_letter.py` (new)
- Prompt: `cover.v1` ([docs/08](../08_PROMPTS_LIBRARY.md))
- Output: `cover_letters/generated/{Company}_{JobID}.txt` + `.pdf`
- Cache by (company) — reuse for similar jobs
- Upload in `apply()` if LinkedIn provides field

### Config
```yaml
ai:
  cover_letter: true
  cover_output_dir: "cover_letters/generated"
```

## 5. Step-by-Step
1. Detect cover letter field in Easy Apply modal
2. Call AI with `cover.v1` + JD + CV + company
3. Parse response (plain text)
4. Validate: word count ≤ 300, no forbidden phrases
5. Save to file + PDF
6. Upload

## 6. Anti-Hallucination
- ✅ Layer 1: Strict prompt
- ✅ Layer 5: Cross-ref skills with resume
- ✅ Layer 7: Audit log

## 7. Checklist
### Build
- [ ] `cover_letter.py`
- [ ] Prompt `cover.v1` in 08_PROMPTS
- [ ] Integration in `apply()`
- [ ] Config flag
### Verify
- [ ] Word count ≤ 300 (auto-truncate)
- [ ] References company by name
- [ ] References 1+ JD-specific detail
- [ ] No skill claimed not in resume

## 8. Acceptance Tests
- [ ] Generate cover letter for 3 jobs
- [ ] Each ≤ 300 words
- [ ] Each references specific JD elements
- [ ] Upload succeeds when field exists

## 9. Log Patterns
```
INFO | 💌 Generated cover letter: <path> (245 words)
WARNING | 💌 Cover letter rejected: 312 words (>300)
INFO | 💌 Uploaded cover letter
```

## 10-12. (see template)
