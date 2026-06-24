# Current State Snapshot

Last verified: 2026-06-24

## Production Summary

The bot is in active local use and the current docs reflect the merged active state of the repo.

| Metric | Value |
|---|---|
| Total applied | 50+ cumulative |
| Saved answers | 138+ |
| Resume tailoring | active |
| Cover letter upload | integrated |
| Fit scoring | integrated in code, disabled in config |
| CV base text length | 6023 chars |
| Supported languages | 8 |
| AI hallucination incidents | 0 verified |

## Confirmed Working

### Detection

- Easy Apply multi-strategy detection
- Already-applied detection
- External apply separation
- Stale element retry paths
- Live Easy Apply button click fallback improvements

### AI

- Question fallback
- Resume tailoring
- Cover letter generation
- Cover letter upload when field exists
- Resume validation
- Fit scoring module in repo
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
- Latest Run progress can update while bot is still running

## Current File Notes

Important active areas:

- `packages/extractors/linkedin.py`
- `apps/worker/runner.py`
- `packages/ai/resume_tailor.py`
- `packages/ai/scorer.py`
- `packages/storage/db.py`
- `apps/web/app.py`
- `apps/web/templates/`

## Known Gaps / Watch Items

| Issue | Status |
|---|---|
| Fit scoring smoke test with `fit_scoring: true` | pending |
| Some LinkedIn modal/button edge cases | monitor |
| Some multilingual form edge cases | partial |
| Smart per-day rate limiting | not implemented yet |
| Dashboard polish beyond current live fixes | pending |

## Historical Context

- A LinkedIn rate-limit incident on 2026-06-24 is documented in [RATE_LIMIT_RECOVERY.md](RATE_LIMIT_RECOVERY.md).
- That document should be treated as operational context and recovery guidance, not as proof of current live cooldown status.

## Notes For Continuation

- `docs/` is canonical.
- Imported bundle context from docs v3.3 was merged selectively.
- Use [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for patch-level truth.
