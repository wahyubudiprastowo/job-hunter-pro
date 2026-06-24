# 📒 Patch History Ledger (v3.1)

Last updated: 2026-06-24 post-Patch 15.

---

## 🧬 Patch Lineage

```
Phase 0 PoC → Phase 1 MVP
    │
Patch 1-3 (Copilot) — EU filters, multi-lang, AI question fallback
Patch 5-8 (External) — Heartbeat, CV extractor, Resume tailoring
Patch 9, 9.1 (Copilot) — Anti-hallucination validator + variant handling
Patch 10 (Copilot) — Cover letter generator
Patch 11, 12 (Copilot) — Comprehensive fixes + validator expansion
Patch 13 (Copilot) — Easy Apply multi-strategy detection
Patch 14 (User) — Already-applied detection ⭐
Patch 15 (User) — CV header phone/links fix ⭐
```

---

## 📜 Patches 1-13
See [v3 docs](https://github.com/wahyubudiprastowo/job-hunter-pro/tree/main/docs) for full details.

---

## ⭐ Patch 14 — Already-Applied Detection (User-implemented)

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | User direct edit |
| Files modified | `packages/extractors/linkedin.py`, `apps/worker/runner.py` |
| Backup | manual via git |
| Risk | 🟢 LOW |

### What's New
- New helper `_detect_already_applied()` in linkedin.py
- Detects markers: "Applied", "Application submitted", "View application" + multi-language variants
- When marker found: job tagged `raw={"already_applied": True}` AND `is_easy_apply=False`
- runner.py distinguishes this as `SkipReason.DUPLICATE` with reason `"already applied on LinkedIn"`
- No longer mis-classified as "external apply"

### Verification (Production)
✅ Log line confirmed: `⏭️  SKIP [IT-System Engineer (m/w/d) @ Greifenberg]: already applied`

### Anti-Breakage Compliance
- ✅ ADDITIVE (new method, no replacements)
- ✅ Backward compatible
- ✅ Apply flow unchanged
- ✅ Verified via `python -m py_compile`

---

## ⭐ Patch 15 — CV Header Phone & Links Fix (User-implemented)

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Source | User direct edit |
| Files modified | `packages/ai/resume_tailor.py` line ~279 |
| Backup | manual via git |
| Risk | 🟢 LOW |

### Bug Fixed
Generated CV header showed:
- `8123456789` (no country code prefix)
- Missing GitHub/Portfolio URLs even when configured

### What's New
- `phone_display` built from `phone_country_code` + `phone` → `+62 8123456789`
- Regex `\+\d+` extracts `+XX` from "Indonesia (+62)" format
- Header now shows `linkedin_url`, `github_url`, `portfolio_url` if configured
- Conditional rendering: empty fields skipped
- Used `getattr(profile, "...", "")` for safe fallback

### Code Pattern Used
```python
if phone_country_code:
    cc_match = re.search(r"\+\d+", phone_country_code)
    if cc_match:
        phone_display = f"{cc_match.group(0)} {phone_raw}"
    else:
        phone_display = f"{phone_country_code} {phone_raw}"
```

### Verification
- ✅ Syntax passed (`python -m py_compile`)
- 🟡 Visual verification: regenerate 1 CV → open PDF → check header

### Anti-Breakage Compliance
- ✅ ADDITIVE (existing fields preserved)
- ✅ Backward compatible (falls back to old format if config missing)
- ✅ Render logic untouched (only header section)
- ✅ No data file changes
- ✅ No selector changes

---

## 🎯 Cumulative Production Status (Post Patch 15)

| Metric | Value |
|---|---|
| Total applies | 50+ confirmed via Gmail |
| Saved answers | 138+ entries |
| CV length | 6023 chars (82 tech terms) |
| Reject rate | 30-40% |
| Languages supported | 8 |
| Easy Apply detection strategies | 5 (Patch 13) |
| Already-applied detection | ✅ Working (Patch 14) |
| CV header phone | ✅ With country code (Patch 15) |
| CV header social links | ✅ LinkedIn/GitHub/Portfolio (Patch 15) |
| AI hallucination incidents | 0 verified |

---

## 🔍 Outstanding Issues

| Issue | Status | Target Patch |
|---|:---:|---|
| Some "external apply" edge cases | 🟡 Improved with P13+14 | Monitor |
| Stuck 67% on Italian/Spanish forms | 🟡 Partially fixed | Manual answer + future Patch |
| Stale element in `_fill_radios` | 🟡 Minor (works on retry) | Patch 18 |
| Dashboard timezone (UTC vs WIB) | ⏭️ Snippet provided | Patch 18 |
| Cover letter LinkedIn upload | ⏭️ Generation done | Patch 16 |
| Phase 2d Fit Scoring | ⏭️ Planned | Patch 17 |
| Phase 3a Ghosting Detector | ⏭️ Planned | Patch 19 |
| Phase 4a Indeed Extractor | ⏭️ Planned | Patch 20 |

---

## 🔗 Related
- [17_CHANGELOG.md](17_CHANGELOG.md)
- [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
- [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)
- [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md)
