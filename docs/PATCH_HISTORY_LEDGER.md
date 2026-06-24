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

## Recent Patches

### Patch 14

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user direct edit |
| Files | `packages/extractors/linkedin.py`, `apps/worker/runner.py` |
| Outcome | already-applied jobs no longer treated as external apply |

Key points:

- Adds explicit already-applied detection logic.
- Tags duplicate jobs distinctly in runner flow.
- Keeps apply flow unchanged for valid jobs.

### Patch 15

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | user direct edit |
| Files | `packages/ai/resume_tailor.py` |
| Outcome | CV header now respects country code and profile links |

Key points:

- Uses `phone_country_code` plus `phone`.
- Renders LinkedIn, GitHub, and portfolio links when configured.
- Keeps backward-compatible fallback behavior.

## Historical Detail

- Earlier detailed forensic notes from the backup bundle were reviewed during docs merge.
- The active docs now preserve the important outcomes without keeping stale status claims.
- For short human-readable release notes, see [17_CHANGELOG.md](17_CHANGELOG.md).

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

