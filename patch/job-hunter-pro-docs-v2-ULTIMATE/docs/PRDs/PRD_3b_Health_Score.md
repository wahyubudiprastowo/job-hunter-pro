# PRD: Phase 3b — Application Health Score

## 0. Status: ⏭️ PLANNED

## 1. Problem
User can't diagnose why response rate is low. Needs holistic view of pipeline health.

## 2. User Story
As a candidate, I want a 0-100 health score with actionable advice ("Response rate dropped 20% this week — refresh resume summary").

## 3. Goals
- ✅ Score 0-100 weighted from 6 factors
- ✅ Display as circular gauge on dashboard
- ✅ Actionable advice text

## 4. Tech Spec
- `packages/ai/health.py` (new)
- Factors: velocity, response_rate, interview_conversion, ghost_penalty, diversity_bonus, ai_quality
- UI: big gauge on /analytics page

## 5. Implementation
```python
weighted = (
    velocity * 0.15 +
    response_rate * 0.30 +
    interview_conversion * 0.30 +
    diversity_bonus * 0.10 +
    ai_quality * 0.15 -
    ghost_penalty * 0.20
)
return max(0, min(100, int(weighted)))
```

## 6. Anti-Hallucination
- Advice text uses templates not free-form AI
- Only refers to factual stats from DB

## 7. Checklist
- [ ] `health.py` with weighted formula
- [ ] UI gauge component
- [ ] Advice generator (template-based)
- [ ] Per-platform breakdown

## 8. Acceptance
- [ ] Score in [0, 100]
- [ ] Factors sum correctly
- [ ] Advice references real data
