# 🔑 MASTER CONTINUITY DOCUMENT

> **READ ME FIRST.** This is the single source of truth for picking up the project
> when conversation history is lost. Any human or AI assistant should be able to
> continue work after reading this document alone.

---

## 🎯 Project Identity

- **Name**: Job-Hunter Pro
- **Repository**: https://gitlab.com/1bulan1m/job-hunter-pro
- **Owner**: Wahyu Budi Prastowo (IT Infrastructure Specialist, Digiserve / Indonesia)
- **Target**: Automate LinkedIn (+ multi-platform) job applications for EU Cloud/DevOps roles
- **Local path (canonical)**: `C:\Users\WP2300419\Documents\VContainer\job-hunter-pro\`
- **Patch folder**: `<project>\patch\job-hunter-pro-patchN\`
- **Docs folder**: `<project>\docs\` ← this folder
- **Web UI**: http://localhost:5050

---

## 📸 Last Known Good State (Snapshot)

As of last verified run (visible in dashboard screenshot):

| Indicator | Value |
|---|---|
| Bot State | RUNNING |
| Applied | 18 |
| Skipped | 47 |
| Needs Answers | 7 |
| Failed | 6 |
| External | 0 |
| Saved Answers | 121 |
| Tailored | 0 (Phase 2b code present but disabled or in test) |
| Diagnostics | State / Command / PID / Heartbeat / Is zombie all WORKING |

### Recent successful applications (real, in production)
- Application & Data Platform Engineer @ Itaú BBA in Europe (Lisbon)
- DevOps Engineer @ RecX B.V. (Delft, Netherlands)
- Systemarchitekt @ The Adecco Group (Kassel)
- DevOps Engineer - AWS Cloud Engineer @ NTT DATA Europe & Latam (Madrid)
- 14 more applied jobs in EU region

**Conclusion**: Application is **stable, in production use**. Do not break it.

---

## 🧬 Current Patch Status

| Patch | Phase | Features | Source | Status |
|---|---|---|---|---|
| Phase 1 MVP | 1 | BaseExtractor, LinkedIn, Flask UI, SQLite, control plane | Copilot conversation | ✅ In repo |
| Patch 1 | 1 | EU filters, diversity auto-decline, robust radios | Copilot conversation | ✅ Applied |
| Patch 2 | 1 | Multi-lang buttons (7 langs), save-dialog auto-discard, stuck detect | Copilot conversation | ✅ Applied |
| Patch 3 | 2a | AI Question Fallback (OpenAI-compatible provider, auto-save learnings) | Copilot conversation | ✅ Applied |
| **Patch 4-8** | **2b** | **Resume Tailoring, Reset State, Test AI, Diagnostics, Heartbeat, Zombie detection** | **External (other LLM/dev session)** | ⚠️ Applied but undocumented |

### What we KNOW about Patch 4-8 from the screenshot (forensic reconstruction)
1. **Phase 2b Resume Tailoring**:
   - File expected: `packages/ai/resume_tailor.py`
   - Counter `tailored: N` added to RunHistory
   - Output dir: `resumes/generated/{Company}_{Title}_{JobID}.pdf`
   - Status: code present, but `tailored: 0` means feature disabled in current config OR not generating yet
2. **Reset State button**: clears `data/.control/state.txt` and `command.txt`
3. **Test AI button**: pings AI provider and reports status
4. **Diagnostics panel**:
   - State (idle/running/paused/stopped)
   - Command (current pending command)
   - PID (process ID of worker)
   - Heartbeat age (seconds since last worker heartbeat write)
   - Is zombie (true if heartbeat > N seconds = stuck)
5. **121 saved answers** suggests AI question fallback (Phase 2a) is running hot
6. **Real EU jobs applied** validates LinkedIn extractor + answer bank working

### How to integrate undocumented patches
See [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) for the protocol to reverse-engineer and document them.

---

## 🚦 What to Work On Next

Read in order:
1. [01_PROJECT_VISION.md](01_PROJECT_VISION.md) — what we're building & why
2. [02_ARCHITECTURE.md](02_ARCHITECTURE.md) — how it's built
3. [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md) — what's actually running RIGHT NOW
4. [PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md) — every patch, every change
5. [12_PHASE_ROADMAP.md](12_PHASE_ROADMAP.md) — what's next & acceptance criteria
6. [PRDs/](PRDs/) — per-feature implementation playbooks
7. [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md) — what you MUST NOT change
8. [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md) — protocol for AI continuity

---

## 🚫 CRITICAL: Do Not Break What Works

Production user is using this **right now**. Before any change:

1. ✅ **Read [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)** in full
2. ✅ **Test on throwaway account first**
3. ✅ **Apply patches via `apply.cmd` (auto-backup)** — never edit in place
4. ✅ **Verify acceptance criteria** in PRD before declaring done
5. ❌ **NEVER touch**: `.chrome-profile/`, `.env`, working selectors without DOM verification
6. ❌ **NEVER reduce**: existing acceptance criteria
7. ❌ **NEVER assume**: read the actual code first

---

## 🛠️ Quick Start (for new developers / AI assistants)

```powershell
# 1. Clone (or pull) repo
cd C:\Users\WP2300419\Documents\VContainer
git clone https://gitlab.com/1bulan1m/job-hunter-pro.git
cd job-hunter-pro

# 2. Setup venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
notepad .env   # fill LINKEDIN_EMAIL, LINKEDIN_PASSWORD, AI_API_KEY

# 4. Drop resume
copy <your-cv-path> resumes\base_resume.pdf

# 5. Run
python run_web.py

# 6. Open dashboard
start http://localhost:5050
```

For VSCode workflow → [VSCODE_GUIDE.md](VSCODE_GUIDE.md).

---

## 🆘 If Something Breaks

1. Stop bot via UI (Stop button)
2. Check `data/logs/bot.log` (last 100 lines)
3. Check `data/screenshots/` for visual debug
4. Search [16_TROUBLESHOOTING.md](16_TROUBLESHOOTING.md)
5. Find most recent backup: `Get-ChildItem .backup_* | Sort-Object Name -Descending`
6. Rollback: copy files from backup folder

---

## 🧠 For AI Assistants Specifically

When you (an AI assistant like Claude / GPT / Gemini / Copilot) pick up this project:

### Mandatory reading order
1. THIS file
2. [AI_HANDOFF_PROTOCOL.md](AI_HANDOFF_PROTOCOL.md)
3. [CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)
4. [ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)
5. [02_ARCHITECTURE.md](02_ARCHITECTURE.md)
6. [05_PLUGIN_SPEC.md](05_PLUGIN_SPEC.md)
7. [20_ANTI_HALLUCINATION.md](20_ANTI_HALLUCINATION.md)

### Before any code change
- Verify the actual file content (don't trust your memory)
- Check git log: `git log --oneline -20` to see recent changes
- Check `docs/PATCH_HISTORY_LEDGER.md` for known modifications
- Read the relevant PRD in `docs/PRDs/`

### When making a patch
- Follow [PRD_TEMPLATE.md](PRD_TEMPLATE.md)
- Create `patch/job-hunter-pro-patchN/` with `apply.cmd`
- Update `docs/17_CHANGELOG.md`
- Update relevant PRD status
- Update `docs/PATCH_HISTORY_LEDGER.md`

---

## 📞 Outdated context warning

If this document is more than **2 patches old**, it may be outdated. Verify:
- Latest entry in [17_CHANGELOG.md](17_CHANGELOG.md)
- Highest patch number in `patch/` folder
- Current GitLab repo state: https://gitlab.com/1bulan1m/job-hunter-pro

---

**Document Version**: 2.0 (ULTIMATE)
**Created**: 2026-06-24
**Patches covered**: 0, 1, 2, 3 (documented) + 4-8 (forensic reconstruction)
