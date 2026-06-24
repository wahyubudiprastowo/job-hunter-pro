# PRD: Phase 3e - CAPTCHA Solver (Patch 25)

## 0. Status
| Field | Value |
|---|---|
| Phase | 3e |
| Status | CODE INTEGRATED (disabled by default; live validation pending) |
| Implementation | Selective bundle merge into active repo |
| Source code | `packages/stealth/captcha_solver.py` |
| Risk | MEDIUM (external provider dependency, real-session validation still needed) |
| Estimate | 30-60 minutes for manual-mode validation, then paid-provider smoke test |

---

## 1. Problem Statement

Indeed and some challenge pages can present CAPTCHAs that break unattended automation.

Before Patch 25:
- Indeed relied on manual waiting in the browser
- unattended runs could stall or timeout
- there was no centralized CAPTCHA logging or cost tracking

Patch 25 adds an additive CAPTCHA solver layer with safe fallback behavior.

---

## 2. Goals

- [x] Detect hCaptcha
- [x] Detect reCAPTCHA v2
- [x] Support `2captcha`
- [x] Support `anticaptcha`
- [x] Support manual fallback mode
- [x] Record solve attempts in SQLite
- [x] Track monthly cost
- [x] Integrate with the current Indeed extractor
- [x] Keep feature disabled by default
- [ ] Validate against a real provider in a live session

---

## 3. Acceptance Criteria

1. [x] `packages/stealth/captcha_solver.py` compiles
2. [x] `test_captcha_solver.py` exists for local verification
3. [x] Runner can initialize solver safely when config exists
4. [x] Indeed extractor can use solver if enabled
5. [x] Manual fallback remains available if solver is disabled or provider fails
6. [x] `captcha_solves` table is created automatically
7. [ ] Real manual-mode validation succeeds in one actual session
8. [ ] Real paid-provider validation succeeds in one actual session

---

## 4. Tech Spec

### 4.1 New Files

- `packages/stealth/captcha_solver.py`
- `test_captcha_solver.py`

### 4.2 Updated Files

- `apps/worker/runner.py`
- `packages/extractors/indeed.py`
- `config.yaml`
- `requirements.txt`

### 4.3 Main Components

```text
detect_captcha(driver)
-> CaptchaInfo

CaptchaSolver.solve(driver, info)
-> provider routing
   - manual
   - 2captcha
   - anticaptcha
-> token injection
-> DB logging
-> SolveResult
```

Primary public helpers:
- `detect_captcha(driver)`
- `CaptchaSolver(...)`
- `solve_if_present(driver, solver)`

---

## 5. Configuration

Current repo-safe scaffold:

```yaml
captcha:
  enabled: false
  provider: "manual"          # manual | 2captcha | anticaptcha
  timeout_seconds: 180
  cost_alert_usd: 5.0
```

Environment variable:

```env
CAPTCHA_API_KEY=your-provider-key
```

Default stays disabled so current behavior does not change until explicitly enabled.

---

## 6. Current Behavior

### If `captcha.enabled: false`
- solver is initialized safely if import succeeds
- Indeed falls back to the prior manual wait behavior
- no paid provider call is made

### If `captcha.enabled: true` and `provider: "manual"`
- solver centralizes detection and manual waiting
- attempts are logged to `captcha_solves`
- no provider cost is incurred

### If `captcha.enabled: true` and provider key exists
- solver can submit hCaptcha or reCAPTCHA v2 to the configured provider
- received token is injected into the page DOM
- cost and duration are logged

---

## 7. Limitations

### 7.1 Live Validation Pending
The code is integrated, but no verified real-session success is claimed yet.

### 7.2 Dashboard/UI Surfacing Not Added
The solver has stats helpers, but dashboard presentation was intentionally not added in this patch.

### 7.3 CAPTCHA Types
Currently targeted:
- hCaptcha
- reCAPTCHA v2

Not yet targeted:
- reCAPTCHA v3
- image CAPTCHA

---

## 8. Testing Strategy

### Local
1. Run `python test_captcha_solver.py`.
2. Confirm all self-tests pass.

### Safe Session
1. Set `captcha.enabled: true`.
2. Set `captcha.provider: "manual"`.
3. Trigger one real CAPTCHA if available.
4. Confirm graceful wait/logging behavior.

### Paid Session
1. Add `CAPTCHA_API_KEY`.
2. Switch provider to `2captcha` or `anticaptcha`.
3. Trigger one real CAPTCHA.
4. Confirm:
   - no crash
   - token injection path runs
   - `captcha_solves` contains the attempt

---

## 9. Anti-Breakage Notes

- additive module only
- disabled by default
- optional import in runner
- fallback to manual mode if provider key is missing
- fallback to old Indeed behavior if solver is disabled
- separate SQLite table, no breaking schema change to `applications`

---

## 10. Cross-References

- [PRD_4a_Indeed.md](PRD_4a_Indeed.md)
- [PRD_4b_Glassdoor.md](PRD_4b_Glassdoor.md)
- [PATCH_HISTORY_LEDGER.md](../PATCH_HISTORY_LEDGER.md)
