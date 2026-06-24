# Changelog

Newest first.

## 2026-06-24 - Patch 19

- added `packages/extractors/rate_limiter.py`
- integrated DB-backed daily cap and cooldown tracking
- added dashboard rate limit status card and reset control
- added runner-side daily cap enforcement and rate-limit detection hook
- adapted patch 19 to the current SQLAlchemy-based repo without large refactor

## 2026-06-24 - Selective Docs v3.3 Merge

- merged long-form context from `job-hunter-pro-docs-v3.3.zip`
- added [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md)
- added [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md)
- refreshed continuity, roadmap, ledger, and snapshot docs
- kept implementation status conservative and aligned to active repo state

## 2026-06-24 - Patch 18

- dashboard now separates latest run information from all-time totals
- latest debug screenshot summary added
- empty-state and refresh UX improved

## 2026-06-24 - Patch 17

- fit scoring module integrated before tailoring
- application detail page can show fit score and reasoning
- DB fields `fit_score` and `fit_reasoning` added
- current status remains partial until real smoke test with `fit_scoring: true`

## 2026-06-24 - Patch 16 and 16.1

- cover letter upload integrated into LinkedIn Easy Apply flow
- generated vs uploaded cover letter counters separated
- cover letter path persisted explicitly

## 2026-06-24 - Docs Merge Cleanup

- merged active docs with the useful context from the archived snapshot
- kept `docs/` as canonical documentation source
- added `DOCS_MERGE_AUDIT.md`
- removed the need to keep a duplicate backup docs tree in the workspace

## 2026-06-24 - Patch 15

- CV header now uses country code with phone number
- CV header can render LinkedIn, GitHub, and portfolio links

## 2026-06-24 - Patch 14

- already-applied jobs are detected and classified separately from external apply

## 2026-06-24 - Patch 13

- Easy Apply detection expanded with multiple strategies and broader language handling

## 2026-06-24 - Patches 9-12

- validator, cover letter, and configuration improvements landed

## 2026-06-23 to 2026-06-24 - Patches 1-8

- LinkedIn automation, multilingual handling, dashboard operations, and tailoring-era capabilities were introduced

See [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for the authoritative patch record.
