# Docs Merge Audit

Date: 2026-06-24  
Workspace: `job-hunter-pro`

## Summary

This audit compares:

- Active docs: `docs/`
- Backup snapshot: `docs.bak_v31_6/02_143251/`
- Incremental patch bundle: `patch/job-hunter-pro-docs-v3.1/docs/`

Conclusion:

- `docs/` should remain the active source of truth.
- `docs.bak_v31_6/02_143251/` was a full historical snapshot, not a newer replacement.
- `patch/job-hunter-pro-docs-v3.1/docs/` is already fully absorbed into `docs/`.
- Full overwrite from `docs.bak_v31_6` is not recommended.

## Comparison Result

### `docs/` vs `docs.bak_v31_6/02_143251/`

- Same files: `49`
- Different files: `6`
- Only in `docs/`: `2`
- Only in backup: `0`

Different files:

- `00_INDEX.md`
- `00_MASTER_CONTINUITY.md`
- `17_CHANGELOG.md`
- `CURRENT_STATE_SNAPSHOT.md`
- `PATCH_HISTORY_LEDGER.md`
- `README.md`

Only in `docs/`:

- `FEATURE_CHECKLIST.md`
- `NEXT_STEPS_ROADMAP.md`

### `docs/` vs `patch/job-hunter-pro-docs-v3.1/docs/`

- Same files: `8`
- Different files: `0`
- Only in patch: `0`

Files already synced from patch v3.1:

- `README.md`
- `00_INDEX.md`
- `00_MASTER_CONTINUITY.md`
- `17_CHANGELOG.md`
- `CURRENT_STATE_SNAPSHOT.md`
- `PATCH_HISTORY_LEDGER.md`
- `FEATURE_CHECKLIST.md`
- `NEXT_STEPS_ROADMAP.md`

## Interpretation

The current `docs/` folder is a merged state:

- It keeps the large v2-style documentation set from the backup snapshot.
- It already includes the v3.1 incremental updates.
- It adds two planning/progress docs that do not exist in the backup snapshot.

So the current situation is not "backup is missing from docs".  
The real situation is "docs already contains backup content plus newer delta docs".

## Done / Not Done

Already merged into `docs/`:

- Full numbered core docs set `00-20`
- Operational continuity docs
- PRD library under `docs/PRDs/`
- v3.1 delta docs from patch bundle
- New progress tracking docs:
  - `FEATURE_CHECKLIST.md`
  - `NEXT_STEPS_ROADMAP.md`

Not yet normalized:

- Backup snapshot still lives separately under `docs.bak_v31_6/02_143251/`
- Six key docs differ between backup and active docs because active docs are shorter v3.1-updated variants
- No single document yet explains this merge status explicitly

## Safe Recommendation

Recommended:

1. Keep `docs/` as canonical.
2. Keep `docs.bak_v31_6/` as archive only.
3. Do not overwrite active docs from backup wholesale.
4. Use this file as the reference for future cleanup.

Optional next cleanup:

1. Fold useful long-form context from backup versions of the 6 differing files into the active versions.
2. Mark `docs.bak_v31_6/` clearly as archive/deprecated.
3. If desired, move the backup snapshot outside the main working area after review.

## Cleanup Status

- `docs.bak_v31_6/` removed after verification
- `patch/job-hunter-pro-docs-v3.1/` kept as patch artifact

## Decision

Current best state:

- Active: `docs/`
- Archive snapshot: removed after audit
- No blind overwrite merge was performed
