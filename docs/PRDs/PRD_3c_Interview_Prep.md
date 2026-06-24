# PRD: Phase 3c — Interview Prep Pack

## 0. Status: ⏭️ PLANNED

## 1. Problem
User wants ready-to-use interview prep when status → INTERVIEW.

## 2. Goals
- ✅ 15+ likely questions
- ✅ STAR-format answer drafts (using REAL resume facts)
- ✅ 5 smart questions to ask interviewer
- ✅ Company research summary
- ✅ Salary negotiation brief
- ✅ Combined into 1 PDF

## 3. Tech Spec
- `packages/ai/interview.py` (new) — 5 sub-prompts
- Trigger: when application status manually marked INTERVIEW
- Output: `data/interview_packs/<job_id>.pdf`
- UI: download button on application detail

## 4. Anti-Hallucination
- STAR drafts MUST cite specific resume facts
- Layer 5: cross-validate against CV
- First 3 packs require manual review

## 5. Checklist
- [ ] `interview.py` with 5 prompts (`interview.v1`)
- [ ] PDF assembly via reportlab
- [ ] Trigger logic
- [ ] UI download endpoint

## 6. Acceptance
- [ ] 15+ questions generated
- [ ] STAR answers cite specific resume bullets
- [ ] No invented experience
