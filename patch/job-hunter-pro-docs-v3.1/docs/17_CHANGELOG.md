# 📜 Changelog (v3.1)

Newest first.

---

## v3.1 Docs Bundle (2026-06-24)

**This bundle**. Updates from v3:
- Add Patches 14 + 15 to ledger
- New FEATURE_CHECKLIST.md (comprehensive)
- New NEXT_STEPS_ROADMAP.md (prioritized plan)
- Updated CURRENT_STATE_SNAPSHOT
- Updated 00_MASTER_CONTINUITY

---

## ⭐ Patch 15 — CV Header Phone & Links Fix (2026-06-24)

**Source**: User direct edit  
**Files**: `packages/ai/resume_tailor.py` line ~279

### Changed
- Phone display now uses `phone_country_code` from config.yaml
  - Format: `+62 8123456789` (was: `8123456789`)
  - Regex extracts `+\d+` from "Indonesia (+62)"
- Header now renders LinkedIn / GitHub / Portfolio URLs
  - All conditional — empty fields skipped
  - Safe fallback via `getattr`

### Why
Previous header had no country code prefix and missing social links.

### Anti-Breakage
- ✅ Additive only
- ✅ Syntax validated (`python -m py_compile`)
- ✅ Backward compatible
- ✅ No DB / config / API changes

---

## ⭐ Patch 14 — Already-Applied Detection (2026-06-24)

**Source**: User direct edit  
**Files**: `packages/extractors/linkedin.py`, `apps/worker/runner.py`

### Added
- `_detect_already_applied()` helper in linkedin.py
- Multi-language markers (Applied, Application submitted, View application, etc.)
- `raw={"already_applied": True}` tagging
- `SkipReason.DUPLICATE` differentiation in runner.py

### Why
Previously: jobs already applied were misclassified as "external apply".
Now: properly tagged as "already applied on LinkedIn".

### Production Verified
✅ Log line confirmed: `⏭️  SKIP [IT-System Engineer @ Greifenberg]: already applied`

---

## Patch 13 — Easy Apply Multi-Strategy Detection (2026-06-24)
- 5 detection strategies (main, class, aria-label, icon, text-search)
- 8 languages (added DE, NL, PT, SV)
- Scroll count 12 (was 6)
- Stale element retry + JS click fallback

## Patch 12 — Validator Expansion (2026-06-24)
- Added scala, java, javascript, bash, powershell, vpn, tls, ssl, sql to whitelist
- cv_diagnostic.py script
- Runner/template snippets

## Patch 11 — Comprehensive Fix (2026-06-24)
- `provider.py` log fix + masking
- `resume_validator.py` COMMON_KNOWLEDGE_TERMS
- `config.yaml` improved
- 5 new answer bank entries
- 6 bugs fixed total

## Patch 10 — Phase 2c Cover Letter (2026-06-24)
- Multi-language cover letter generation (7 langs)
- 7 anti-hallucination checks
- Cache by company

## Patch 9.1 — Variant Fix (2026-06-24)
- 11 variant groups

## Patch 9 — Anti-Hallucination Validator (2026-06-24)
- 200+ tech database
- 5 validation checks

## Patches 1-8 (2026-06-23 to 24)
- See v2/v3 docs for details

---

## 🎯 Roadmap

### Next Patches
- **Patch 16**: Cover Letter LinkedIn Upload (Phase 2c → DONE)
- **Patch 17**: Phase 2d Fit Scoring
- **Patch 18**: UI/UX improvements (timezone, stats)
- **Patch 19**: Phase 3a Ghosting Detector
- **Patch 20**: Phase 4a Indeed Extractor

See [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md) for full plan.

---

## 🔗 Related
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)
- [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
- [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md)
