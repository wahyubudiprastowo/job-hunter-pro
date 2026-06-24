# PRD: Phase 2d — AI Job Fit Scoring

## 0. Status
| Field | Value |
|---|---|
| Phase | 2d |
| Status | ⏭️ PLANNED |
| Patch | TBD |

## 1. Problem Statement
Bot wastes effort applying to jobs that don't fit. User wants pre-filter that skips poor matches before AI tailoring + apply.

## 2. User Story
As a candidate, before each apply, I want AI to score job fit 0-100 with explanation. Skip if < threshold (configurable). Show score in dashboard.

## 3. Goals & Non-Goals
### Goals
- ✅ Score 0-100
- ✅ Explanation in 2-3 sentences
- ✅ List matched vs missing skills
- ✅ Recommendation: STRONG_APPLY / APPLY / MAYBE / SKIP
- ✅ Configurable threshold (skip if < N)
### Non-Goals
- ❌ Replace human judgment for borderline scores
- ❌ Hide low-fit jobs from history (still log as SKIPPED)

## 4. Tech Spec
- `packages/ai/scorer.py` (new)
- Prompt: `score.v1` ([docs/08](../08_PROMPTS_LIBRARY.md))
- DB: add columns `fit_score`, `fit_reasoning`
- New SkipReason: `FIT_SCORE_LOW`
- UI: gauge component on detail page

### Config
```yaml
ai:
  fit_scoring: true
  fit_threshold: 60
```

## 5. Step-by-Step
1. After `open_job_detail`, before filters: call scorer
2. Parse JSON response
3. If score < threshold → skip with `FIT_SCORE_LOW`
4. Else store score + reasoning, proceed
5. UI: show colored gauge per app

## 6. Anti-Hallucination
- ✅ Layer 1: Strict prompt
- ✅ JSON parsing strict
- ✅ matched ∩ missing must be empty
- ✅ score range [0, 100]
- ✅ recommendation aligned with score

## 7. Checklist
### Build
- [ ] `scorer.py`
- [ ] DB migration: 2 new columns
- [ ] New SkipReason enum
- [ ] Filter integration in runner.py
- [ ] UI gauge in application_detail.html
- [ ] Config keys
### Verify
- [ ] Valid JSON 100% of time
- [ ] Score in [0, 100]
- [ ] Reasoning aligns with score
- [ ] Threshold filter works
- [ ] UI gauge color-codes

## 8. Acceptance Tests
- [ ] 10 jobs scored, all valid JSON
- [ ] No conflicts (matched ∩ missing empty)
- [ ] Skip rate ↑ for tight thresholds
- [ ] Reasoning explainable to user

## 9. Log Patterns
```
INFO | 🎯 Fit score: 87/100 [STRONG_APPLY]
INFO | 🎯 Fit score: 45/100 [SKIP] → skipping
```

## 10-12. (see template)
