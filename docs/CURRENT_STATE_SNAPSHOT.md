# Current State Snapshot

Last verified: 2026-06-24

## Production Summary

The bot is in active use and the current docs reflect the live merged state of the repo.

| Metric | Value |
|---|---|
| Total applied | 50+ cumulative |
| Typical applied per run | 6-10 |
| Saved answers | 138+ |
| Resume tailoring | active |
| CV base text length | 6023 chars |
| Supported languages | 8 |
| AI hallucination incidents | 0 verified |

## Confirmed Working

### Detection

- Easy Apply multi-strategy detection
- Already-applied detection
- External apply separation
- Stale element retry paths

### AI

- Question fallback
- Resume tailoring
- Cover letter generation
- Resume validation
- Multi-language handling

### Output Quality

- CV phone uses country code
- CV can include LinkedIn, GitHub, and portfolio links
- ATS-oriented formatting remains intact

### Operations

- Dashboard controls
- Heartbeat and zombie detection
- Run cleanup
- SQLite-backed application history

## Current File Notes

Important active areas:

- `packages/extractors/linkedin.py`
- `apps/worker/runner.py`
- `packages/ai/resume_tailor.py`
- `packages/storage/db.py`
- `apps/web/app.py`
- `apps/web/templates/`

## Known Non-Blocking Gaps

| Issue | Status |
|---|---|
| Some edge-case external/apply classification | monitor |
| Some multilingual form edge cases | partial |
| Some stale-element retries still noisy | minor |
| Dashboard time and aggregate stats need polish | pending |

## Notes For Continuation

- `docs/` is canonical.
- The old `docs.bak_v31_6` snapshot was reviewed as archive only.
- Use [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for patch-level truth.

