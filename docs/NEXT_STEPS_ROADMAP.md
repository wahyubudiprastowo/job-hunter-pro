# 🚀 Next Steps Roadmap (Post Patch 15)

Last updated: 2026-06-24

---

## 🎯 Prioritized Roadmap

### Tier 1 — Quick Wins (1-2 days each)

#### Patch 16 — Cover Letter LinkedIn Upload
**Status**: ⏭️ NEXT  
**Phase**: 2c (complete Phase 2c)  
**Estimate**: 1-2 days  
**Risk**: 🟢 LOW

**Scope**:
- Detect cover letter field in LinkedIn Easy Apply modal
  - Textarea: `textarea[id*='cover'], textarea[name*='cover']`
  - File input: `input[type='file'][name*='cover']`
- Upload `cover_letters/generated/{Company}_{JobID}.pdf` when field detected
- Multi-language label detection:
  - EN: "Cover Letter"
  - IT: "Lettera di presentazione"
  - DE: "Anschreiben"
  - ES: "Carta de presentación"
  - FR: "Lettre de motivation"
- DB schema: ensure `cover_letter_path` column populated
- Counter: `cover_letters_uploaded` in run summary
- Log markers: `💌 Uploaded cover letter: <path>`

**Impact**: Phase 2c → ✅ DONE. Response rate likely +20%.

**Acceptance**:
- [ ] Cover letter field detected on 5+ test jobs
- [ ] PDF uploaded successfully
- [ ] Bot still applies when field absent
- [ ] Counter increments correctly

---

#### Patch 18 — UI/UX Improvements
**Status**: ⏭️ AFTER P16  
**Phase**: Tier 0 (continuity)  
**Estimate**: 1 day  
**Risk**: 🟢 LOW (UI only)

**Scope**:
- Dashboard timezone fix (UTC → WIB)
  - Backend: Jinja filter `local_time(7)`
  - OR Frontend: JavaScript date conversion
- Per-session vs cumulative counters distinction
- Better "stuck screenshot" review link in UI
- Confirmation modal for "Reset State"
- Better empty-state messaging
- Stale element error: graceful UI feedback

**Impact**: Better daily-use UX. No backend changes.

**Acceptance**:
- [ ] "When" column shows WIB time
- [ ] Counters distinguish run vs total
- [ ] Reset State requires confirmation

---

### Tier 2 — Strategic Features (2-3 days each)

#### Patch 17 — Phase 2d Fit Scoring
**Status**: ⏭️ AFTER P16  
**Phase**: 2d (NEW)  
**Estimate**: 2-3 days  
**Risk**: 🟡 MEDIUM (DB schema change)

**Why**: Saves AI cost — skip irrelevant jobs **before** tailoring + cover letter generation.

**Scope**:
- `packages/ai/scorer.py` with `score.v1` prompt
- Score 0-100 per job
- Output JSON: `{score, matched_skills, missing_skills, red_flags, reasoning, recommendation}`
- Skip if `score < ai.fit_threshold` (default 60)
- New SkipReason `FIT_SCORE_LOW`
- DB columns: `fit_score`, `fit_reasoning`
- Filter integration: BEFORE resume tailoring (cost optimization)
- UI gauge in `application_detail.html` (color-coded)
- Config keys: `ai.fit_scoring`, `ai.fit_threshold`
- Cache per job_id

**Impact**: 
- Phase 2d → ✅ DONE
- ~30% reduction in AI calls (cost saving)
- Better job prioritization

**Acceptance**:
- [ ] Valid JSON 100% of calls
- [ ] Score in [0, 100]
- [ ] matched ∩ missing = empty
- [ ] Skip rate ↑ with tight threshold
- [ ] UI gauge color-codes correctly

---

#### Patch 19 — Phase 3a Ghosting Detector
**Status**: ⏭️ AFTER P17  
**Phase**: 3a (NEW)  
**Estimate**: 3 days  
**Risk**: 🟡 MEDIUM

**Why**: Unique selling point. Helps you avoid wasting time on companies that ghost.

**Scope**:
- `packages/ai/ghosting.py` (pure logic, no AI needed initially)
- DB columns: `viewed_by_recruiter`, `last_response_at`, `last_response_type`
- GhostStatus enum: ACTIVE / SLOW / LIKELY_GHOSTED / GHOSTED / REJECTED / INTERVIEW / OFFER
- Status calculator: based on days since apply + recruiter view + response type
- Per-company ghost rate aggregation
- UI badges in history table (color-coded)
- Warning before re-applying to ghoster
- Phase 3d hook: notify on transition to LIKELY_GHOSTED

**Impact**:
- Phase 3a → ✅ DONE
- Pipeline visibility
- Smarter job targeting

**Acceptance**:
- [ ] Status transitions correctly
- [ ] Ghost rate 0-100%
- [ ] Re-apply warning shown

---

### Tier 3 — Expansion (1 week each)

#### Patch 20 — Phase 4a Indeed Extractor
**Status**: ⏭️ AFTER P19  
**Phase**: 4a (NEW)  
**Estimate**: 1 week  
**Risk**: 🟠 HIGH (new platform)

**Why**: 2× job sources. Validate plugin architecture.

**Scope**:
- `packages/extractors/indeed.py`
- Login (with hCaptcha handling)
- Search with Indeed-specific filters
- Card collection
- Detail extraction
- Apply flow (Indeed Apply iframe)
- hCaptcha integration (2Captcha)
- EXTRACTOR_REGISTRY update
- Config block `platforms.indeed.*`
- `.env`: `INDEED_EMAIL`, `INDEED_PASSWORD`

**Dependencies**:
- Phase 3e CAPTCHA Solver (concurrent dev)

**Acceptance**:
- [ ] Login succeeds
- [ ] Search returns ≥ 5 cards
- [ ] Detail extracts properly
- [ ] Apply succeeds ≥ 1 job
- [ ] No regression in LinkedIn

---

### Tier 4 — Enterprise Hardening (multi-week)

#### Patch 21 — Phase 3d Notifications Hub
**Estimate**: 4 days
**Scope**: APScheduler + 5 channels (Email, Telegram, Teams, Discord, Webhook)

#### Patch 22 — Phase 5 Security Hardening
**Estimate**: 3 days
**Scope**: AES-256 vault, pre-commit hook, audit log

#### Patch 23 — Phase 5 CI/CD
**Estimate**: 5 days
**Scope**: GitLab CI pipeline with full test + scan + deploy

---

## 📊 Timeline (Realistic)

```
Week 1 (current):
  ✅ Patch 14, 15 (DONE)
  → Patch 16: Cover letter upload
  → Patch 18: UI improvements

Week 2:
  → Patch 17: Phase 2d Fit Scoring
  → Patch 19: Phase 3a Ghosting Detector

Week 3-4:
  → Patch 20: Phase 4a Indeed

Week 5-6:
  → Patch 21: Notifications Hub
  → Patch 22: Security Hardening

Week 7-8:
  → Patch 23: CI/CD
  → Phase 5 polish (dark mode, i18n, PWA)

Total estimate: ~8 weeks part-time to reach v1.0
```

---

## 🚦 Decision Points

### When to ship Phase 2 → Phase 3?
**Trigger**: 100+ real applies submitted, response rate ≥ 15%

### When to add Indeed (Phase 4a)?
**Trigger**: LinkedIn fully stable, no critical bugs for 1 week

### When to migrate Postgres (Phase 5)?
**Trigger**: SQLite DB > 100 MB OR multi-tenant required

### When to add CI/CD (Phase 5)?
**Trigger**: Going public, OR 2+ developers, OR enterprise customer

---

## 🎯 What to Start NOW

Based on:
- Production usage stability ✅
- Phase 2b just completed ✅
- Phase 2c 90% done (only upload missing) 🟡

**Recommended**: **Patch 16 (Cover Letter Upload)** — completes Phase 2c.
Quick win, low risk, immediate impact on response rate.

Then **Patch 17 (Fit Scoring)** — saves cost + improves quality.

---

## 🔗 Related
- [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md) — what's done
- [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) — patch history
- [12_PHASE_ROADMAP.md](12_PHASE_ROADMAP.md) — full phase plan
- [PRDs/](PRDs/) — detailed PRDs per feature
