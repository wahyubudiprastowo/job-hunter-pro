# PRD: Phase 3a — Ghosting Detector

## 0. Status: ⏭️ PLANNED

## 1. Problem
Companies often go silent after apply. User wants to flag these so they can deprioritize.

## 2. User Story
As a candidate, I want to see per-company ghost rate and per-app ghost status, so I know which companies to avoid re-applying to.

## 3. Goals
- ✅ Track days since apply per job
- ✅ Auto-status: ACTIVE / SLOW / LIKELY_GHOSTED / GHOSTED / REJECTED / INTERVIEW / OFFER
- ✅ Per-company ghost rate (%)
- ✅ UI badges in history table
- ✅ Warning before re-applying to known ghosters

## 4. Tech Spec
- `packages/ai/ghosting.py` (new) — pure logic, no AI needed
- DB columns: `viewed_by_recruiter`, `last_response_at`, `last_response_type`
- New endpoint: `/api/ghost-rate/<company>`
- UI: badge per app row

## 5. Implementation
1. Schedule daily background job (Phase 3d scheduler) to recalc status
2. For each application:
   ```python
   days = (now - applied_at).days
   if last_response_type == "REJECT": status = REJECTED
   elif days > 30: status = GHOSTED
   elif days > 14 and viewed and not response: status = LIKELY_GHOSTED
   elif days > 7: status = SLOW
   else: status = ACTIVE
   ```
3. Aggregate per company

## 6. Checklist
- [ ] `ghosting.py` with status calc
- [ ] DB migration: 3 new columns
- [ ] Status enum in models.py
- [ ] UI badges color-coded
- [ ] Company ghost rate query
- [ ] Warning UI on re-apply attempt

## 7. Acceptance
- [ ] Status calc correct for all 7 states
- [ ] Ghost rate 0-100%
- [ ] Notification on transition to LIKELY_GHOSTED

## 12. Cross-refs
- [04_DATA_MODELS.md](../04_DATA_MODELS.md) GhostStatus enum
