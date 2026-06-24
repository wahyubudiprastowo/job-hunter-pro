# PRD: Phase 4a - Indeed Extractor (Patch 22)

## 0. Status
| Field | Value |
|---|---|
| Phase | 4a |
| Status | CODE INTEGRATED (disabled by default; first live validation pending) |
| Implementation | Selective bundle merge into active repo |
| Source code | `packages/extractors/indeed.py` |
| Risk | HIGH (new platform, hCaptcha unpredictability) |
| Estimate | 30-60 minutes smoke validation after credentials are configured |

---

## 1. Problem Statement

LinkedIn rate limit incident on 2026-06-24 proved:
- single-platform dependency = single point of failure
- account ban or cooldown can stall all applying activity
- redundancy is valuable, but only if integrated conservatively

Indeed adds:
- a second job source alongside LinkedIn
- different anti-bot behavior from LinkedIn
- strong EU market coverage
- an "Apply with Indeed" style quick-apply flow
- a real validation target for the extractor/plugin architecture

---

## 2. User Story

As a candidate, I want the bot to:
1. apply to both LinkedIn and Indeed in the same overall architecture
2. reuse the same resume, cover letter, and answer bank patterns
3. classify Indeed quick apply vs external apply safely
4. fall back to manual captcha solving when Indeed blocks automation

---

## 3. Goals

- [x] `BaseExtractor` implementation exists
- [x] Login flow added with captcha solver hook plus manual fallback
- [x] Multi-region domain support (`indeed.com`, `de.indeed.com`, etc.)
- [x] Search URL builder and card collection
- [x] Detail extraction
- [x] Indeed Apply detection
- [x] External apply classification path
- [x] Resume upload path
- [x] Cover letter upload path (reuses Patch 16 pattern)
- [x] AI question fallback hook (reuses Patch 3 pattern)
- [x] Debug screenshot path
- [x] Runner registration
- [x] `config.yaml` scaffold added
- [ ] First real login validation
- [ ] First successful Indeed apply

---

## 4. Acceptance Criteria

1. [x] Module compiles
2. [x] Implements the `BaseExtractor` contract
3. [ ] Login succeeds with real credentials
4. [ ] Search returns at least 5 cards for a common query
5. [ ] Detail extraction works for title/company/description/salary
6. [ ] At least 1 successful Indeed apply is verified
7. [ ] External apply jobs are skipped cleanly
8. [ ] No regression in LinkedIn flow
9. [x] Backward compatibility preserved when Indeed remains disabled

---

## 5. Tech Spec

### 5.1 Module Architecture

```text
packages/extractors/indeed.py
|- BTN_APPLY_NOW / BTN_CONTINUE / BTN_SUBMIT
|- SELECTORS
|- DATE_CODE
|- EXP_CODE
`- class IndeedExtractor(BaseExtractor)
```

Key methods:
- `login()`
- `_check_captcha()` / `_wait_for_manual_captcha()`
- `search()` / `_build_search_url()`
- `collect_job_cards()`
- `open_job_detail()`
- `_detect_indeed_apply()`
- `apply()`
- `_switch_to_ia_frame()`
- `_upload_resume_ia()`
- `_upload_cover_letter_ia()`
- `_fill_text_inputs_ia()`
- `_fill_selects_ia()`
- `_fill_radios_ia()`
- `_fill_checkboxes_ia()`
- `_lookup_answer()`
- `_save_ai_answer()`
- `_screenshot_for_debug()`

### 5.2 Integration Points

- `packages/extractors/indeed.py` added
- `apps/worker/runner.py` optionally imports and registers Indeed
- `config.yaml` now includes `platforms.indeed`
- credentials expected in `.env`:
  - `INDEED_EMAIL`
  - `INDEED_PASSWORD`
  - `INDEED_TOTP_SECRET` (optional)

### 5.3 Apply Flow

```text
click Apply now
-> switch into Indeed Apply iframe
-> upload resume
-> upload cover letter if field exists
-> fill form fields from profile / answer bank / AI fallback
-> continue or submit
-> verify confirmation
```

---

## 6. Configuration

Current repo-safe scaffold:

```yaml
platforms:
  indeed:
    enabled: false
    max_apply_per_run: 5
    scroll_count: 8
    region: ""
    search:
      queries:
        - "Cloud Infrastructure Engineer"
        - "DevOps Engineer"
        - "Azure Engineer"
      location: "Berlin, Germany"
      remote: false
      hybrid: false
      date_posted: "past_week"
      experience_levels:
        - "Mid level"
        - "Senior level"
      job_type: "Full-time"
      easy_apply_only: true
```

Default is intentionally disabled so current LinkedIn behavior does not change until the user explicitly opts in.

---

## 7. Limitations and Mitigations

### 7.1 hCaptcha
Issue:
- Indeed can show hCaptcha unpredictably.

Current mitigation:
- Patch 25 can now attempt solver-assisted handling, with manual fallback preserved

Future:
- live validation of Patch 25 inside real Indeed sessions

### 7.2 Geographic Restrictions
Issue:
- Indonesian IP applying to EU jobs may look suspicious

Mitigation:
- use regional domain such as `region: "de"`
- or use a VPN aligned with the target market

### 7.3 Lower Practical Daily Cap
Issue:
- Indeed may tolerate fewer applications per day than LinkedIn

Mitigation:
- start with a very small cap
- validate with `max_apply_per_run: 1` first

---

## 8. Testing Strategy

### Smoke Test
1. Set `platforms.linkedin.enabled: false` temporarily if needed.
2. Add Indeed credentials to `.env`.
3. Change `platforms.indeed.enabled: true`.
4. Set `platforms.indeed.max_apply_per_run: 1`.
5. Run one tiny session only.

### Verify
- login completes
- results page returns cards
- a job detail opens
- quick-apply modal or iframe is detected
- any failure produces a screenshot/log instead of crashing the run

### Regression
- turn Indeed back off
- confirm LinkedIn-only mode still works unchanged

---

## 9. Anti-Breakage Notes

- additive module only
- optional import in runner
- safe disabled default in config
- no DB schema change required
- reuses existing answer-bank, fit-scoring, cover-letter, and rate-limiter pipeline

---

## 10. Cross-References

- [05_PLUGIN_SPEC.md](../05_PLUGIN_SPEC.md)
- [PRD_3e_Captcha_Solver.md](PRD_3e_Captcha_Solver.md)
- [PRD_SmartRateLimiter.md](PRD_SmartRateLimiter.md)
- [PATCH_HISTORY_LEDGER.md](../PATCH_HISTORY_LEDGER.md)
