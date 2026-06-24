# PRD: Phase 4a — Indeed Extractor

## 0. Status: ⏭️ PLANNED

## 1. Problem
Adding Indeed expands job coverage beyond LinkedIn.

## 2. Goals
- ✅ Implement `BaseExtractor` contract for Indeed
- ✅ Multi-language buttons if applicable
- ✅ Handle platform-specific quirks: Aggressive hCaptcha — leans on Phase 3e

## 3. Tech Spec
- `packages/extractors/indeed.py` (new)
- Register in `EXTRACTOR_REGISTRY` in runner.py
- New config block: `platforms.indeed.*`
- New env vars: `INDEED_EMAIL`, `INDEED_PASSWORD`

## 4. Implementation Order
1. Read [05_PLUGIN_SPEC.md](../05_PLUGIN_SPEC.md)
2. Inspect platform's search URL + DOM structure
3. Implement 6 abstract methods
4. Test in safe_auto mode on 3 jobs
5. Centralize selectors in module-level dict
6. Update config + .env example

## 5. Anti-Breakage
- Don't change other extractors
- Add to EXTRACTOR_REGISTRY as addition, not replacement
- Backward compat for existing data shape

## 6. Checklist
- [ ] All 6 methods implemented
- [ ] SELECTORS centralized
- [ ] Multi-lang if needed
- [ ] Login handles 2FA + CAPTCHA
- [ ] Config block + .env vars
- [ ] Updated EXTRACTOR_REGISTRY
- [ ] PATCH_HISTORY_LEDGER updated

## 7. Acceptance
- [ ] Login succeeds
- [ ] Search returns ≥ 5 cards
- [ ] Open detail extracts title/company/desc
- [ ] Apply succeeds ≥ 1 job
- [ ] No regression in LinkedIn extractor

## 8. Risks
- Platform-specific: Aggressive hCaptcha — leans on Phase 3e
- DOM changes — centralize selectors

## 9. Cross-Refs
- [05_PLUGIN_SPEC.md](../05_PLUGIN_SPEC.md) — interface
- [16_TROUBLESHOOTING.md](../16_TROUBLESHOOTING.md) — per-platform pitfalls
