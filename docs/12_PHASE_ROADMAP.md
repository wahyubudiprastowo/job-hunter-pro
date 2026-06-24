# 🗺️ Phase Roadmap

See [PRDs/INDEX.md](PRDs/INDEX.md) for per-feature PRDs with full detail.

## Phase 0 — PoC ✅ DONE
Single-file login + 1 apply.

## Phase 1 — MVP ✅ DONE
BaseExtractor, LinkedIn, Flask UI, SQLite, control plane.

## Phase 2 — AI Pro
- **2a** ✅ Question Fallback ([PRD](PRDs/PRD_2a_Question_Fallback.md))
- **2b** 🟡 Resume Tailoring ([PRD](PRDs/PRD_2b_Resume_Tailoring.md)) — code present, output=0
- **2c** ⏭️ Cover Letter ([PRD](PRDs/PRD_2c_Cover_Letter.md))
- **2d** ⏭️ Fit Scoring ([PRD](PRDs/PRD_2d_Fit_Scoring.md))

## Phase 3 — Differentiators
- **3a** ⏭️ Ghosting Detector ([PRD](PRDs/PRD_3a_Ghosting_Detector.md))
- **3b** ⏭️ Health Score ([PRD](PRDs/PRD_3b_Health_Score.md))
- **3c** ⏭️ Interview Prep ([PRD](PRDs/PRD_3c_Interview_Prep.md))
- **3d** ⏭️ Scheduler + Notifications ([PRD](PRDs/PRD_3d_Scheduler_Notifications.md))
- **3e** ⏭️ CAPTCHA Solver ([PRD](PRDs/PRD_3e_Captcha_Solver.md))

## Phase 4 — Multi-Platform
- 4a Indeed, 4b Glassdoor, 4c JobStreet, 4d Wellfound, 4e ATS
- 4f Multi-Tenant, 4g REST API

## Phase 5 — Enterprise
CI/CD, Postgres, Vault, K8s, i18n, PWA.

## Cumulative Timeline
~12 weeks part-time, ~6 weeks full-time.

## Phase Gates
| Going to | Must pass |
|---|---|
| 2c | 2b: 0 hallucinations in 5 audits |
| 3 | 2 stable 1 week, no critical bugs |
| 4 | LinkedIn stable, AI cost predictable |
| 5 | 100+ applies on multi-platform |

## 🔗 [13_CHECKLIST_LIBRARY.md](13_CHECKLIST_LIBRARY.md)
