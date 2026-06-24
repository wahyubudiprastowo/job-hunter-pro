# PRD: Phase 2d - AI Job Fit Scoring

## 0. Status
| Field | Value |
|---|---|
| Phase | 2d |
| Status | Partial - code integrated, runtime validation pending |
| Patch | 17 |

## 1. Problem Statement
Bot wastes effort applying to jobs that do not fit. User wants a pre-filter that scores fit before resume tailoring and cover letter generation, so low-fit jobs are skipped earlier and AI cost stays lower.

## 2. User Story
As a candidate, before each apply, I want AI to score job fit from 0-100 with a short explanation, then skip jobs below a configurable threshold and store the score so I can audit why the bot skipped or continued.

## 3. Goals & Non-Goals
### Goals
- Score 0-100
- Explanation in 2-3 sentences
- List matched vs missing skills
- Recommendation: `APPLY`, `MAYBE`, or `SKIP`
- Configurable threshold (`skip if score < N`)
- Cache score per job to reduce repeated AI cost

### Non-Goals
- Replace human judgment for borderline scores
- Hide low-fit jobs from history
- Full dashboard charts/gauges in Patch 17

## 4. Tech Spec
- `packages/ai/scorer.py` adds fit scoring logic
- Prompt is embedded as `SCORE_SYSTEM_PROMPT` in scorer module
- DB adds columns `fit_score`, `fit_reasoning`
- New `SkipReason`: `FIT_SCORE_LOW`
- UI adds fit score + reasoning on application detail page
- Cache location: `data/fit_scores/{job_id}.json`

### Config
```yaml
ai:
  fit_scoring: false
  fit_threshold: 60
  fit_score_output_dir: "data/fit_scores"
```

## 5. Actual Flow
1. Existing cheap filters run first: company, title, duplicate, description, salary, already-applied, can-auto-apply.
2. After `open_job_detail()` and after those cheap filters, scorer runs.
3. AI JSON response is parsed and normalized.
4. If score < threshold, bot records `FIT_SCORE_LOW` and skips.
5. If score >= threshold, bot stores score/reasoning and continues to resume tailoring, cover letter generation, and apply.
6. Application detail page shows stored fit score and reasoning.

## 6. Anti-Hallucination / Validation Rules
- Strict JSON parsing
- Score must be integer in `[0, 100]`
- Recommendation normalized to `APPLY | MAYBE | SKIP`
- `matched_skills` and `missing_skills` are sanitized to string lists
- Overlap between matched and missing is removed
- Cache loading must tolerate extra metadata fields

## 7. Checklist
### Build
- [x] `scorer.py`
- [x] DB migration: `fit_score`, `fit_reasoning`
- [x] New `SkipReason.FIT_SCORE_LOW`
- [x] Runner integration before tailoring
- [x] Detail page fit score display
- [x] Config keys

### Verify
- [ ] Real run with `fit_scoring: true`
- [ ] Valid JSON on real runs
- [ ] Reasoning aligns with score
- [ ] Threshold filter works
- [ ] Low-fit skip path works without crash
- [ ] Score visible on real application detail records

## 8. Acceptance Tests
- [ ] 10 jobs scored successfully
- [ ] No `matched_skills ∩ missing_skills` conflict
- [ ] Skip rate increases when threshold is tightened
- [ ] `fit_score` and `fit_reasoning` persist to DB
- [ ] Cached score is reused on second run

## 9. Expected Log Patterns
```text
SUCCESS | Fit scoring ENABLED - threshold: 60
INFO    | Fit score: 87/100 (HIGH) [Cloud Engineer @ Example] -> APPLY
INFO    | SKIP [Cloud Engineer @ Example]: fit score 45 < threshold 60
```

## 10. Current Implementation Notes
- Current code already passes `fit_score_output_dir` from `config.yaml`.
- Current code stores fit data for applied jobs and low-fit skipped jobs.
- Current code integrates fit scoring before resume tailoring, which is the intended cost-saving point.
- Current live log from 2026-06-24 shows Patch 17 code is present, but `fit_scoring` is still disabled in config, so runtime validation has not happened yet.

## 11. Patch 17 Review Notes
- Optimization adopted from external Patch 17 zip:
  - recommendation normalization
  - skill-list sanitizing
  - overlap cleanup between matched and missing
  - cache-load tolerance for extra metadata fields
- Local fix added during review:
  - `_record_skip_full(..., **extra)` and `_record_skip(..., **extra)` now safely forward `fit_score` / `fit_reasoning`
  - this prevents a crash when low-fit skip path is hit after enabling `fit_scoring`

## 12. Deferred / Future
- Dashboard-level fit charts or gauges remain a later UI patch.
- Threshold tuning should happen only after 1-2 real scored runs.
