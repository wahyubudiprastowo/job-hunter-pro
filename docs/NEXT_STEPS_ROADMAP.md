# Next Steps Roadmap

Last updated: 2026-06-24

## Recently Completed

- Patch 16: Cover Letter Upload Integration
- Patch 16.1: Cover letter persistence and counters review fixes
- Patch 17: Phase 2d Fit Scoring integrated in code
- Patch 18: Dashboard UX improvements

## Important Operational Context

- A LinkedIn rate-limit incident was documented on 2026-06-24.
- Recovery and lessons learned are captured in [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md).
- Do not assume current live cooldown unless the current UI/logs confirm it, but do treat account-safety work as a top priority.

## Priority Reordered

### Tier 0 - Validate What Already Landed

#### A1. Patch 17 Production Validation
Status: ready, pending small real run  
Estimate: 1 hour  
Risk: low

Actions:

1. Enable `fit_scoring: true` in `config.yaml`.
2. Run one small session only.
3. Verify:
   - `fit_score` and `fit_reasoning` persisted
   - `FIT_SCORE_LOW` skip works cleanly
   - no crash or bad classification
4. Tune threshold after observing real distribution.

#### A2. Monitor Latest LinkedIn Fixes
Status: active verification  
Estimate: 1 short run  
Risk: medium

Actions:

1. Verify `Latest Run` now updates while run is active.
2. Verify true external apply jobs still land in `external`.
3. Verify jobs with visible Easy Apply do not get mislabeled as `external/not_easy_apply`.

### Tier 1 - Smart Rate Limiter

#### Patch 19 - Smart Rate Limiter
Status: next target  
Estimate: 4-6 hours  
Risk: medium

Why now:

- It is the best direct response to the previously documented LinkedIn rate-limit incident.
- It protects account safety better than simply lowering caps by hand.

Primary reference:

- [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md)

Core scope:

- daily cap tracking per platform
- rate-limit message detection
- auto-pause / cooldown
- persistent safety state across runs
- dashboard visibility for cap/cooldown state

### Tier 2 - Phase 3a Ghosting Detector

#### Patch 20 - Ghosting Detector
Status: after Patch 19  
Estimate: 3 days  
Risk: medium

Why after Patch 19:

- safety and stability first
- can benefit from fit score context once Patch 17 is validated

### Tier 3 - UI Modernization

#### Patch 21 - UI Modernization
Status: after Patch 20  
Estimate: 1-2 days  
Risk: low

Why later:

- better to modernize UI after fit score and rate-limit data are visible and stable

### Tier 4 - Multi-Platform Expansion

#### Patch 22 - Indeed Extractor
Status: after Patch 21  
Estimate: 1-2 weeks  
Risk: high

Dependencies:

- stable LinkedIn behavior
- rate-limiter guardrails
- enough bandwidth to support another platform safely

## Timeline

```text
Now:
  - verify Patch 17 on a small run
  - verify latest LinkedIn external/apply fixes
  - keep Smart Rate Limiter as next real patch

Next:
  - Patch 19 Smart Rate Limiter
  - Patch 20 Ghosting Detector
  - Patch 21 UI Modernization

Later:
  - Patch 22 Indeed Extractor
```

## Decision Framework

### When to enable Patch 17 fully?
Trigger: one safe test run available and current LinkedIn state looks stable.

### When to ship Patch 19?
Trigger: immediately after Patch 17 smoke test, or in parallel as planning if runtime validation must wait.

### When to add Indeed?
Trigger: LinkedIn flow stable for at least several runs and Smart Rate Limiter is in place.

## Related

- [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
- [PRDs/PRD_2d_Fit_Scoring.md](PRDs/PRD_2d_Fit_Scoring.md)
- [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md)
- [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md)
