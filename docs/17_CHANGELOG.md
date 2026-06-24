# 📜 Changelog

Newest first.

## v2 Docs Bundle ULTIMATE (2026-06-24)
**This bundle**. Reorganized + new docs for continuity:
- NEW: 00_MASTER_CONTINUITY.md (AI handoff)
- NEW: CURRENT_STATE_SNAPSHOT.md (production state)
- NEW: PATCH_HISTORY_LEDGER.md (with Patch 4-8 inferred)
- NEW: ANTI_BREAKAGE_RULES.md
- NEW: AI_HANDOFF_PROTOCOL.md
- NEW: VSCODE_GUIDE.md
- NEW: GITLAB_INTEGRATION.md
- NEW: PRD_TEMPLATE.md + 17 per-feature PRDs
- Updated all tier docs (compact, link-rich)

## Patches 4-8 [INFERRED — undocumented in this conversation]
Per evidence in dashboard screenshot:
- Patch 4: Reset State button
- Patch 5: Test AI button
- Patch 6: Diagnostics panel (PID/heartbeat/zombie)
- Patch 7: Worker heartbeat writer
- Patch 8: Phase 2b Resume Tailoring + startup speed fix

**ACTION REQUIRED**: User to share Patch 4-8 source code so they can be properly documented in [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md).

## Patch 3 — Phase 2a AI Question Fallback (2026-06-23)
- ADD: `packages/ai/provider.py`, `question_bot.py`
- MOD: `linkedin.py::_lookup_answer` step 6
- MOD: `runner.py` instantiate AIProvider
- MOD: `config.yaml` `ai:` block
- Validated: 121 saved answers in production

## Patch 2 — Multi-Language + Save-Dialog (2026-06-23)
- Multi-lang buttons (EN/IT/ES/FR/DE/PT/NL)
- Save dialog auto-Discard
- Stuck detection
- Resume auto-selection
- Progress logging

## Patch 1 — EU + Diversity Auto-Decline (2026-06-23)
- Auto-decline diversity questions
- Robust radio labels
- Multi-strategy submit verification
- Debug screenshots
- Filter improvements

## Phase 1 MVP (2026-06-23)
- Full repo skeleton (47 files)
- BaseExtractor + LinkedIn
- Flask dashboard
- Validated: applied to TRANSATEL

## Phase 0 PoC (2026-06-23)
- Single-file login + apply

## Upcoming
See [PRDs/INDEX.md](PRDs/INDEX.md).

## 🔗 [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
