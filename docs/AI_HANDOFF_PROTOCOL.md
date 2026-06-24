# 🤝 AI Handoff Protocol

For AI assistants (Claude / GPT / Gemini / Copilot / Cursor / etc.) picking up this project.

---

## 🎯 Your Mission as AI Assistant

You are working on a **production application** that:
- Has real EU job applications submitted (18+)
- Has a growing answer bank (121 entries)
- User trusts the bot to act on their behalf
- Anti-hallucination is **mandatory**, not optional

Treat every change as if you're handling someone's career.

---

## 📚 Mandatory Reading (in order)

Before writing any code:

1. **[00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md)** — orient yourself
2. **[CURRENT_STATE_SNAPSHOT.md](CURRENT_STATE_SNAPSHOT.md)** — know what works now
3. **[PATCH_HISTORY_LEDGER.md](PATCH_HISTORY_LEDGER.md)** — know what changed when
4. **[ANTI_BREAKAGE_RULES.md](ANTI_BREAKAGE_RULES.md)** — know what you must not touch
5. **[20_ANTI_HALLUCINATION.md](20_ANTI_HALLUCINATION.md)** — know your AI honesty duty
6. **[02_ARCHITECTURE.md](02_ARCHITECTURE.md)** — understand the design
7. **The PRD for the feature you're working on** (`docs/PRDs/`)

If you skip any of these, you risk breaking production.

---

## 🧪 Self-Check Before Coding

Answer YES to ALL before writing code:

- [ ] I have read 00_MASTER_CONTINUITY.md
- [ ] I have read CURRENT_STATE_SNAPSHOT.md
- [ ] I have read the PRD for the feature I'm working on
- [ ] I have read ANTI_BREAKAGE_RULES.md
- [ ] I have read the relevant existing code (not memory!)
- [ ] I understand which acceptance criteria I need to hit
- [ ] I know which files I'll modify
- [ ] I know which files I MUST NOT modify
- [ ] I have a rollback plan

If any NO → don't code yet.

---

## 🗣️ How to Communicate

### Be honest about uncertainty
- ❌ "Patch 8 already includes X"
- ✅ "I don't have Patch 8 source in this docs bundle. Need to verify against repo or ask user to share."

### Cite sources
- ❌ "The function should return JSON"
- ✅ "Per docs/08_PROMPTS_LIBRARY.md `score.v1`, function returns JSON with fields: score, matched_skills, ..."

### Flag risks
- ❌ "I'll add a new selector"
- ✅ "Adding new selector. Risk: LOW (additive only). Rollback: remove the new entry from SELECTORS dict."

### Ask before destroying
- ❌ Silently delete file
- ✅ "About to delete `packages/extractors/old_module.py`. Confirm?"

---

## 🛠️ Standard Workflow

### For a new feature

```
1. Read PRD in docs/PRDs/PRD_<phase>_<feature>.md
   ↓
2. Read existing files you'll modify
   git show HEAD:<file>  OR  cat <file>
   ↓
3. Verify acceptance criteria are clear
   ↓
4. Implement in patch/job-hunter-pro-patchN/
   ↓
5. Test manually (safe_auto mode first)
   ↓
6. Verify checklist in PRD
   ↓
7. Update:
   - docs/17_CHANGELOG.md
   - docs/PATCH_HISTORY_LEDGER.md
   - docs/PRDs/<this-feature>.md (status → done)
   ↓
8. Commit + push to GitLab
   ↓
9. Inform user
```

### For a bug fix

```
1. Reproduce
   ↓
2. Read data/logs/bot.log
   ↓
3. Read data/screenshots/ if visual issue
   ↓
4. Identify minimal change
   ↓
5. Check ANTI_BREAKAGE_RULES.md (don't break in fixing)
   ↓
6. Create patch
   ↓
7. Verify
```

---

## 🚦 Decision Matrix

When user asks for something, decide:

| User request type | Action |
|---|---|
| "Make bot faster" | Tune existing knobs (delays, caps) before code change |
| "Add new platform" | Follow PLUGIN_SPEC.md, drop file in extractors/ |
| "Better AI prompt" | Version it: `question.v2`, don't replace v1 |
| "Fix this bug" | Identify root cause + minimal patch |
| "What's broken" | Read CURRENT_STATE_SNAPSHOT.md first |
| "Where are we" | Read PATCH_HISTORY_LEDGER.md first |
| Unclear | Ask user before coding |

---

## 🛑 When to Refuse

You should push back if user asks for:
- Removing anti-hallucination guards
- Hardcoding credentials in config.yaml
- Increasing apply rate above safety caps without throttling
- Inventing skills on resume
- Bypassing CAPTCHA aggressively
- Removing audit logging

Be polite but firm. Explain why. Suggest alternative.

---

## 📝 When Updating Docs

### Always update
- `17_CHANGELOG.md` — semantic description of change
- `PATCH_HISTORY_LEDGER.md` — patch entry
- The PRD you implemented from

### Maybe update
- `CURRENT_STATE_SNAPSHOT.md` — if state changed significantly
- `02_ARCHITECTURE.md` — if structural change
- `04_DATA_MODELS.md` — if data shapes changed
- `10_CONFIGURATION_SPEC.md` — if config keys added

### Almost never update without consent
- `01_PROJECT_VISION.md` — vision should be stable
- `20_ANTI_HALLUCINATION.md` — strengthen yes, weaken no

---

## 🔄 Continuity Test

Before declaring your work done, ask yourself:

> "If conversation history disappeared right now, could a different AI assistant
> read the docs I updated and continue from where I left off, WITHOUT breaking
> production?"

If NO → your docs aren't sufficient. Add more.

---

## 🧠 Memory & Context Limits

You probably have:
- Limited context window (200K-1M tokens)
- Limited tool access (depending on platform)
- No memory between sessions (unless explicit memory tool)

**Mitigation**:
- Trust **docs files first**, your training data second
- Re-read docs at the START of each long session
- When in doubt, ask user for current state
- Output your understanding back to user for verification

---

## 🤝 Honest Disclosure to User

If you don't have full context:

> "I see patches 0-3 are documented in this bundle. The dashboard shows
> features (Reset State, Test AI, Diagnostics, Heartbeat) that suggest
> Patches 4-7 were applied externally. To proceed safely, I need either:
> (a) source code of Patches 4-7 from your repo, or
> (b) explicit OK to reverse-engineer from GitLab https://gitlab.com/1bulan1m/job-hunter-pro"

---

## 🔗 Related
- [00_MASTER_CONTINUITY.md](00_MASTER_CONTINUITY.md)
- [PRD_TEMPLATE.md](PRD_TEMPLATE.md)
- [20_ANTI_HALLUCINATION.md](20_ANTI_HALLUCINATION.md)
