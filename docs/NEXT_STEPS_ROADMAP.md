# Next Steps Roadmap

Last updated: 2026-06-24

## Recently Completed

- Patch 16: Cover Letter Upload Integration
- Patch 16.1: Cover letter persistence and counters review fixes
- Patch 17: Phase 2d Fit Scoring integrated in code
- Patch 18: Dashboard UX improvements
- Patch 19: Smart Rate Limiter integrated in code
- Patch 22: Indeed extractor integrated in code (disabled by default)
- Patch 25: CAPTCHA solver integrated in code (disabled by default)

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

### Tier 1 - Validate Patch 19 In Real Run

#### A3. Patch 19 Runtime Validation
Status: ready, awaiting live confirmation  
Estimate: 1 short run  
Risk: medium

Actions:

1. Lower `total_apply_per_day` temporarily for test if needed.
2. Confirm cap persists across restart.
3. Confirm dashboard card shows current state correctly.
4. Confirm no regression in normal apply flow.

#### A4. Patch 22 Indeed Smoke Validation
Status: ready, awaiting first safe Indeed login/apply test  
Estimate: 30-60 minutes  
Risk: high

Actions:

1. Add `INDEED_EMAIL` and `INDEED_PASSWORD` to `.env`.
2. Enable Indeed only for a tiny smoke run.
3. Start with `max_apply_per_run: 1`.
4. Verify login, card collection, and at least one real form open before trusting larger runs.

#### A5. Patch 25 CAPTCHA Solver Validation
Status: ready, awaiting local/manual then paid-provider validation  
Estimate: 30-60 minutes  
Risk: medium

Actions:

1. Run `python test_captcha_solver.py`.
2. Test `captcha.provider: "manual"` first.
3. Add `CAPTCHA_API_KEY` only after manual mode is clean.
4. Verify `captcha_solves` rows are written and failures degrade gracefully.

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
Status: code integrated, first live validation pending  
Estimate: 30-60 minutes smoke test + follow-up tuning  
Risk: high

Dependencies:

- valid Indeed credentials
- first captcha/login verification
- rate-limiter guardrails still in place

## Timeline

```text
Now:
  - verify Patch 17 on a small run
  - verify latest LinkedIn external/apply fixes
  - validate Patch 19 in a short real run
  - smoke-test Patch 22 on Indeed with cap=1
  - validate Patch 25 in manual mode before enabling paid solving

Next:
  - Patch 20 Ghosting Detector
  - Patch 21 UI Modernization

Later:
  - expand multi-platform only after Indeed smoke validation is stable
```

## Decision Framework

### When to enable Patch 17 fully?
Trigger: one safe test run available and current LinkedIn state looks stable.

### When to ship Patch 19?
Trigger: immediately after Patch 17 smoke test, or in parallel as planning if runtime validation must wait.

### When to add Indeed?
Trigger: after credentials are set, first captcha/login verification succeeds, and one small Indeed smoke test is clean.

### When to enable paid CAPTCHA solving?
Trigger: after `test_captcha_solver.py` passes and manual fallback mode behaves cleanly in one real session.

## Related

- [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
- [PRDs/PRD_2d_Fit_Scoring.md](PRDs/PRD_2d_Fit_Scoring.md)
- [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md)
- [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md)
