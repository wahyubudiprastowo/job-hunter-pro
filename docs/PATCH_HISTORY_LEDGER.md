# Patch History Ledger

This is the authoritative log for patch lineage and patch documentation rules.

Last updated: 2026-06-24

## Patch Lineage

```text
Phase 0 PoC
  -> Phase 1 MVP
  -> Patch 1
  -> Patch 2
  -> Patch 3
  -> Patches 5-8
  -> Patch 9
  -> Patch 9.1
  -> Patch 10
  -> Patch 11
  -> Patch 12
  -> Patch 13
  -> Patch 14
  -> Patch 15
  -> Patch 16
  -> Patch 16.1
  -> Patch 17
  -> Patch 18
  -> Patch 19
```

## Summary By Group

| Patch Range | Summary |
|---|---|
| Phase 0 / MVP | initial automation proof and repo skeleton |
| 1-3 | filters, multilingual handling, AI answer fallback |
| 5-8 | dashboard controls, heartbeat, diagnostics, tailoring-era additions |
| 9-13 | anti-hallucination, cover letter, validators, Easy Apply detection |
| 14 | already-applied detection |
| 15 | CV header phone and profile links fix |
| 16 / 16.1 | cover letter upload plus minor counter/persistence fixes |
| 17 | fit scoring integration |
| 18 | dashboard UX improvements |
| 19 | smart rate limiter integration |

## Recent Patches

### Patch 16

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user-directed implementation |
| Files | extractor base, LinkedIn extractor, runner, db, application detail UI |
| Outcome | cover letter generation and upload path integrated end-to-end |

Key points:

- Detects cover letter field in LinkedIn Easy Apply flow.
- Uploads PDF or fills textarea depending on field type.
- Persists `cover_letter_path` in DB and shows it in detail UI.

### Patch 16.1

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user-requested minor review fixes |
| Files | `apps/worker/runner.py`, `packages/storage/db.py` |
| Outcome | counters and persistence behavior are clearer and safer |

Key points:

- Adds `cover_letters_generated` counter.
- Passes `cover_letter_path` explicitly to persistence layer.
- Adds debug logging for skipped apply returns.

### Patch 17

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user integration + external patch context |
| Files | scorer module, models, db, runner, config, application detail UI |
| Outcome | fit scoring integrated conservatively before tailoring |

Key points:

- Adds `packages/ai/scorer.py`.
- Adds `fit_score` and `fit_reasoning` DB fields.
- Adds `SkipReason.FIT_SCORE_LOW`.
- Integrates fit scoring before tailoring and cover letter generation.
- Current status remains conservative: code integrated, smoke test still pending with `fit_scoring: true`.

### Patch 18

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user-requested dashboard improvements |
| Files | `apps/web/app.py`, `apps/web/templates/dashboard.html` |
| Outcome | dashboard better distinguishes latest run, screenshots, and empty states |

Key points:

- Adds `Latest Run` panel.
- Adds latest debug screenshot panel.
- Improves empty-state messaging and dashboard snapshot UX.

### Patch 19

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | selective integration from external patch19 bundle |
| Files | rate limiter module, models, db, runner, app, dashboard template, config |
| Outcome | DB-backed daily cap and cooldown protection integrated without major refactor |

Key points:

- Adds `packages/extractors/rate_limiter.py`.
- Adds `SkipReason.DAILY_CAP_REACHED`.
- Initializes isolated `rate_limits` table in SQLite.
- Enforces per-platform daily cap across runs.
- Adds dashboard visibility and reset control for limiter state.
- Bundle self-test adapted and verified: 15/15 passed in `.venv`.

## Imported v3.3 Context

The v3.3 docs bundle added useful planning context that has now been merged selectively:

- `RATE_LIMIT_RECOVERY.md`
- `PRDs/PRD_SmartRateLimiter.md`
- expanded roadmap and incident context

Those imported docs are useful, but verified repo state still wins if any status wording conflicts.

## Historical Incident Notes

- A LinkedIn rate-limit incident on 2026-06-24 is documented in [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md).
- Treat that as historical operational context until a current run/log explicitly shows the same condition again.

## Rules For Future Patch Documentation

After a real patch is applied:

1. Update this ledger.
2. Update [17_CHANGELOG.md](17_CHANGELOG.md).
3. Update any relevant PRD under `docs/PRDs/`.
4. Update continuity docs if production behavior changed.

## Orphan Patch Detection

A patch is orphaned if:

- code changed but no entry exists here
- dashboard behavior changed but continuity docs still describe older behavior
- a patch artifact exists without matching documentation

When that happens:

1. inspect the current code
2. reconstruct the behavior
3. document only verified facts
4. avoid guessing production status
