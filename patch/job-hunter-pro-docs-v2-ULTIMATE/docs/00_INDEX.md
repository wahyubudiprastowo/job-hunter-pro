# 📚 Job-Hunter Pro Documentation — Master Index

**Bundle**: v2 ULTIMATE
**Date**: 2026-06-24
**Repo**: https://gitlab.com/1bulan1m/job-hunter-pro

---

## 🚨 START HERE

If you're new (or AI assistant picking up project):

1. **[00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md)** — single-doc entry point
2. **[CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)** — production reality now
3. **[ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)** — what NOT to break
4. **[AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md)** — for AI assistants

---

## 🗂️ Document Tiers

### Tier 0 — Continuity (critical for handoff)
| Doc | Purpose |
|---|---|
| [00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md) | AI/dev entry point |
| [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md) | What's running NOW |
| [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) | Every patch tracked |
| [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md) | Don't break production |
| [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md) | AI continuity |
| [VSCODE_GUIDE.md](VSCODE_GUIDE.md) | Local dev setup |
| [GITLAB_INTEGRATION.md](GITLAB_INTEGRATION.md) | Repo workflow |

### Tier 1 — Foundation
| # | Doc | Purpose |
|---|---|---|
| 01 | [PROJECT_VISION](01_PROJECT_VISION.md) | North star |
| 02 | [ARCHITECTURE](02_ARCHITECTURE.md) | Layered design |
| 03 | [TECH_STACK](03_TECH_STACK.md) | All libraries |
| 04 | [DATA_MODELS](04_DATA_MODELS.md) | Pydantic + SQL |

### Tier 2 — Specifications
| # | Doc | Purpose |
|---|---|---|
| 05 | [PLUGIN_SPEC](05_PLUGIN_SPEC.md) | BaseExtractor contract |
| 06 | [UI_UX_SPEC](06_UI_UX_SPEC.md) | All routes + pages |
| 07 | [AI_SPEC](07_AI_SPEC.md) | AI layer detail |
| 08 | [PROMPTS_LIBRARY](08_PROMPTS_LIBRARY.md) | All prompts versioned |
| 09 | [API_REFERENCE](09_API_REFERENCE.md) | REST + web routes |
| 10 | [CONFIGURATION_SPEC](10_CONFIGURATION_SPEC.md) | Every config knob |

### Tier 3 — Operational
| # | Doc | Purpose |
|---|---|---|
| 11 | [SECURITY_PRIVACY](11_SECURITY_PRIVACY.md) | Threat model + anti-detect |
| 12 | [PHASE_ROADMAP](12_PHASE_ROADMAP.md) | Phases 0-5 |
| 13 | [CHECKLIST_LIBRARY](13_CHECKLIST_LIBRARY.md) | Per-phase verification |
| 14 | [DEVOPS_CICD](14_DEVOPS_CICD.md) | Docker + CI/CD |
| 15 | [TESTING_QA](15_TESTING_QA.md) | Test strategy |
| 16 | [TROUBLESHOOTING](16_TROUBLESHOOTING.md) | Common issues |

### Tier 4 — Reference
| # | Doc | Purpose |
|---|---|---|
| 17 | [CHANGELOG](17_CHANGELOG.md) | Patch semantic history |
| 18 | [DEVELOPMENT_GUIDE](18_DEVELOPMENT_GUIDE.md) | Dev setup |
| 19 | [GLOSSARY](19_GLOSSARY.md) | Terms |
| 20 | [ANTI_HALLUCINATION](20_ANTI_HALLUCINATION.md) | AI safeguards |

### Tier 5 — Per-Feature PRDs ⭐ NEW in v2
| Phase | PRD |
|---|---|
| 2a ✅ | [PRD_2a_Question_Fallback](PRDs/PRD_2a_Question_Fallback.md) |
| 2b 🟡 | [PRD_2b_Resume_Tailoring](PRDs/PRD_2b_Resume_Tailoring.md) |
| 2c ⏭️ | [PRD_2c_Cover_Letter](PRDs/PRD_2c_Cover_Letter.md) |
| 2d ⏭️ | [PRD_2d_Fit_Scoring](PRDs/PRD_2d_Fit_Scoring.md) |
| 3a ⏭️ | [PRD_3a_Ghosting_Detector](PRDs/PRD_3a_Ghosting_Detector.md) |
| 3b ⏭️ | [PRD_3b_Health_Score](PRDs/PRD_3b_Health_Score.md) |
| 3c ⏭️ | [PRD_3c_Interview_Prep](PRDs/PRD_3c_Interview_Prep.md) |
| 3d ⏭️ | [PRD_3d_Scheduler_Notifications](PRDs/PRD_3d_Scheduler_Notifications.md) |
| 3e ⏭️ | [PRD_3e_Captcha_Solver](PRDs/PRD_3e_Captcha_Solver.md) |
| 4a-e ⏭️ | [PRDs/](PRDs/) (5 platforms) |
| 4f ⏭️ | [PRD_4f_Multi_Tenant](PRDs/PRD_4f_Multi_Tenant.md) |
| 4g ⏭️ | [PRD_4g_REST_API](PRDs/PRD_4g_REST_API.md) |
| 5 ⏭️ | [PRD_5_Enterprise](PRDs/PRD_5_Enterprise.md) |
| Template | [PRD_TEMPLATE.md](PRD_TEMPLATE.md) |

---

## 📸 Current Production Status

✅ **18 real EU job applications submitted**
✅ **121 saved answers** (AI learning growing)
🟡 **Tailored counter: 0** (Phase 2b code present, not yet active)
✅ **Diagnostics + Reset State + Test AI buttons working**

See [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md) for full snapshot.

---

## 🧬 Patch Status

| Patch | Phase | Source | Status |
|---|---|---|---|
| MVP | 1 | Documented in this bundle | ✅ |
| 1 | 1 | Documented | ✅ |
| 2 | 1 | Documented | ✅ |
| 3 | 2a | Documented | ✅ |
| 4-8 | 2b+UI | **External — needs source** | ⚠️ |

See [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for full ledger + Reverse-Engineering Protocol.

---

## 🚦 What to Work On Next

1. **Verify Patch 4-8** in repo (read actual code, document)
2. **Enable Phase 2b** (currently `tailored: 0`)
3. **Phase 2c** Cover Letter ([PRD](PRDs/PRD_2c_Cover_Letter.md))
4. **Phase 2d** Fit Scoring ([PRD](PRDs/PRD_2d_Fit_Scoring.md))

---

**Maintenance**: Update [17_CHANGELOG.md](17_CHANGELOG.md) + [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) on every patch.
