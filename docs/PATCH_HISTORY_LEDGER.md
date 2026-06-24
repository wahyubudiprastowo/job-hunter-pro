# 📒 Patch History Ledger

Authoritative log of **every patch ever applied** to the project. This file MUST be updated when any code change ships.

If a patch exists in repo but not in this ledger → it's "orphan". Use the **Reverse-Engineering Protocol** at the bottom of this doc.

---

## 🧬 Patch Lineage (chronological)

```
Phase 0 PoC
    │
    ▼
Phase 1 MVP (initial bundle)
    │
    ▼
Patch 1 — EU filters + diversity
    │
    ▼
Patch 2 — Multi-lang + save-dialog
    │
    ▼
Patch 3 — Phase 2a AI Question Fallback
    │
    ▼ ⚠️ HISTORY GAP (Patches 4-8 applied externally)
    │
    ▼
Patch 4 — [INFERRED] Reset State button + UI extensions
Patch 5 — [INFERRED] Test AI endpoint
Patch 6 — [INFERRED] Diagnostics panel (PID, heartbeat, zombie)
Patch 7 — [INFERRED] Worker heartbeat writer
Patch 8 — [INFERRED] Phase 2b Resume Tailoring + startup speed fix
    │
    ▼ (current production state)
```

---

## 📜 Detailed Patch Log

### Patch 0 — PoC (Phase 0)
| Field | Value |
|---|---|
| Status | ✅ Superseded by MVP |
| Date | 2026-06-23 |
| Source | Copilot conversation |
| Files | Single `runAiBot.py` |
| Notes | Validated login + 1 apply works |

### Patch — Phase 1 MVP Bundle
| Field | Value |
|---|---|
| Status | ✅ In production |
| Date | 2026-06-23 |
| Bundle | `job-hunter-pro-phase1.zip` |
| Source | Copilot conversation |
| Files added | Full repo skeleton (47 files) |
| Key features | BaseExtractor, LinkedIn, Flask UI, SQLite, control plane |
| Acceptance | ✅ Apply 1 job to TRANSATEL succeeded |

### Patch 1 — EU + Diversity Auto-Decline
| Field | Value |
|---|---|
| Status | ✅ Applied |
| Date | 2026-06-23 |
| Bundle | `job-hunter-pro-patch1.zip` |
| Source | Copilot conversation |
| Files changed | `packages/extractors/linkedin.py`, `config.yaml`, `data/answers.json` |
| Backup folder | `.backup_p1_<ts>/` |
| Key changes | Diversity auto-decline, robust radio labels, multi-strategy verify, debug screenshots |

### Patch 2 — Multi-Language + Save-Dialog
| Field | Value |
|---|---|
| Status | ✅ Applied |
| Date | 2026-06-23 |
| Bundle | `job-hunter-pro-patch2.zip` |
| Source | Copilot conversation |
| Files changed | `packages/extractors/linkedin.py`, `data/answers.json` |
| Backup folder | `.backup_p2_<ts>/` |
| Key changes | 7 languages, save dialog auto-discard, stuck detection, resume auto-select, progress log |

### Patch 3 — Phase 2a AI Question Fallback
| Field | Value |
|---|---|
| Status | ✅ Applied |
| Date | 2026-06-23 |
| Bundle | `job-hunter-pro-patch3.zip` |
| Source | Copilot conversation |
| Files added | `packages/ai/{__init__,provider,question_bot}.py` |
| Files changed | `packages/extractors/linkedin.py`, `apps/worker/runner.py`, `config.yaml` |
| Backup folder | `.backup_p3_<ts>/` |
| Key changes | OpenAI-compatible client, AI question fallback, auto-save learnings, cooldown |

### Patch 4 — [INFERRED] Reset State Button
| Field | Value |
|---|---|
| Status | ⚠️ Applied externally, undocumented |
| Date | Unknown |
| Bundle | Unknown (not in Copilot history) |
| Source | External LLM session or manual edit |
| Files likely changed | `apps/web/app.py` (new endpoint), `apps/web/templates/dashboard.html` (button) |
| Evidence | "🔄 Reset State" button visible in dashboard screenshot |
| Backup folder | Possibly `.backup_p4_<ts>/` (verify in project) |
| **Need source** | Yes — see Reverse-Engineering Protocol below |

### Patch 5 — [INFERRED] Test AI Button
| Field | Value |
|---|---|
| Status | ⚠️ Applied externally, undocumented |
| Files likely changed | `apps/web/app.py` (new endpoint `/api/test-ai`), dashboard.html |
| Evidence | "🧪 Test AI" button visible in dashboard |
| **Need source** | Yes |

### Patch 6 — [INFERRED] Diagnostics Panel
| Field | Value |
|---|---|
| Status | ⚠️ Applied externally, undocumented |
| Files likely changed | `apps/web/app.py` (new endpoint `/api/diagnostics`), dashboard.html, `apps/worker/control.py` |
| Evidence | Diagnostics card with State/Command/PID/Heartbeat/Is zombie visible |
| **Need source** | Yes |

### Patch 7 — [INFERRED] Worker Heartbeat
| Field | Value |
|---|---|
| Status | ⚠️ Applied externally, undocumented |
| Files likely changed | `apps/worker/runner.py` (heartbeat writer thread), `apps/worker/control.py` (read heartbeat) |
| Evidence | "Heartbeat age: 3.1s" + "Is zombie: No" visible |
| **Need source** | Yes |

### Patch 8 — [INFERRED] Phase 2b Resume Tailoring + Startup Speed
| Field | Value |
|---|---|
| Status | ⚠️ Applied externally, undocumented (per user's PATCH_NOTES sample) |
| Files likely added | `packages/ai/resume_tailor.py`, `config.snippet.yaml` |
| Files likely changed | `packages/stealth/browser.py` (startup speed), `apps/worker/runner.py` (integration), `config.yaml` (ai.resume_tailoring flag) |
| Evidence | Counter `tailored: 0` in run summary log |
| Output dir | `resumes/generated/{Company}_{Title}_{JobID}.pdf` |
| Status of feature | Code present but not generating (config disabled or test mode) |
| **Need source** | Yes |

---

## 🔍 Reverse-Engineering Protocol

When a patch was applied externally and you need to integrate it into this docs bundle:

### Step 1: Identify gap
```powershell
# Check what patch folders exist in project
Get-ChildItem patch -Directory | Select-Object Name

# Check what backup folders exist (each = one patch was applied)
Get-ChildItem .backup_* -Directory | Sort-Object Name
```

### Step 2: Read actual code from repo
```powershell
git pull origin main
git log --oneline -30  # see recent commits
```

For each suspicious file, read the current content vs. what's in docs:

```powershell
# Files that may have changed in Patch 4-8:
$files = @(
    "apps/web/app.py",
    "apps/web/templates/dashboard.html",
    "apps/worker/runner.py",
    "apps/worker/control.py",
    "packages/ai/resume_tailor.py",
    "packages/stealth/browser.py",
    "config.yaml"
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "=== $f ==="
        Get-Content $f | Select-Object -First 30
    }
}
```

### Step 3: Diff against last known state
```powershell
git log --all --pretty=format:"%h %s" -- packages/ai/resume_tailor.py
git show <commit-hash>:packages/ai/resume_tailor.py
```

### Step 4: Extract & document
For each undocumented patch:

1. Read the actual code
2. Fill in the patch entry above with real values
3. Create matching PRD: `docs/PRDs/PRD_<phase>_<feature>.md`
4. Add entry to `docs/17_CHANGELOG.md`
5. Mark patch as ✅ Documented (not ⚠️ Inferred)

### Step 5: Verify acceptance
Run the acceptance tests from the PRD. If they pass → patch is verified. If not → fix or roll back.

---

## 🚨 Orphan Detection

A patch is "orphan" if:
- It modified files but no entry exists here
- A backup folder `.backup_pN_*` exists with no matching ledger entry
- Production has features not described in any PRD

**Action when orphan found**:
1. Stop new development
2. Run Reverse-Engineering Protocol
3. Document the orphan
4. Verify it doesn't conflict with planned features
5. Only then resume

---

## 📤 How to Document a Future Patch

After applying any patch, **before declaring done**:

1. Append entry above with full table
2. Update `docs/17_CHANGELOG.md`
3. Update relevant PRD in `docs/PRDs/`
4. Commit to GitLab with message: `docs: ledger entry for patch N`
5. If undocumented features → bump major doc version (v2 → v3)

---

## 🔗 Related
- [17_CHANGELOG.md](17_CHANGELOG.md) — User-facing changelog
- [PRDs/](PRDs/) — Implementation playbooks
- [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md) — Don't break working features
