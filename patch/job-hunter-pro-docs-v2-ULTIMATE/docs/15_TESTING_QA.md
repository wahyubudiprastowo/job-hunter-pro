# 🧪 Testing & QA

## Test Pyramid (Phase 5)
- Unit: ~100 tests
- Integration: ~30 tests
- E2E: ~5 tests (manual now, scripted P5)

## Unit Tests (P5)
- `test_filters.py`, `test_question_bot.py`, `test_resume_validator.py`
- `test_humanizer.py`, `test_config_validation.py`

## E2E Manual

### Phase 1
1. docker compose up
2. Click Start
3. Watch logs for APPLIED
4. Stop

### Phase 2a
+ Look for 🤖 / 💾 in logs
+ answers.json grew
+ Re-run, same Qs NOT re-asked

### Phase 2b (when active)
+ resumes/generated/ has new PDF per job
+ Diff vs base: no new tech
+ Counter `tailored: N > 0`

## Acceptance Patterns
- "GIVEN X, WHEN Y, THEN Z"
- "X MUST NOT Y"

## Coverage Target
- P1-2: manual smoke
- P3-4: 50% unit
- P5: 80% combined

## 🔗 [13_CHECKLIST_LIBRARY.md](13_CHECKLIST_LIBRARY.md)
