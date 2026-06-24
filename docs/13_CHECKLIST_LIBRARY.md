# ✅ Checklist Library

Per-phase verification. Each PRD has its own checklist; this aggregates.

## Phase 1 — MVP ✅
See [PRD acceptance criteria, all met].

## Phase 2a ✅
- [x] AI provider initializes
- [x] Bot works with AI disabled
- [x] AI cooldown triggers
- [x] Auto-save persists
- [x] No hallucinations observed

## Phase 2b 🟡
- [ ] Verify `resume_tailor.py` exists in repo (run `Get-ChildItem packages/ai/`)
- [ ] Set `ai.resume_tailoring: true` in config.yaml
- [ ] Run bot, check log for `🎨 Resume tailoring ENABLED`
- [ ] Counter `tailored: N` where N > 0
- [ ] Anti-hallucination diff validator works (no new tech in 3 generations)
- [ ] PDF renders correctly
- [ ] Tailored uploaded, not base

## Phase 2c, 2d
See individual PRDs.

## Phase 3, 4, 5
See individual PRDs in [PRDs/](PRDs/).

## New Platform Quick Checklist
- [ ] Read [05_PLUGIN_SPEC.md](05_PLUGIN_SPEC.md)
- [ ] Inspect platform's URL + DOM
- [ ] Note language requirements
- [ ] Create `packages/extractors/<name>.py`
- [ ] Implement 6 methods
- [ ] Register in EXTRACTOR_REGISTRY
- [ ] Add config + .env
- [ ] Test in safe_auto mode

## 🔗 [12_PHASE_ROADMAP.md](12_PHASE_ROADMAP.md)
