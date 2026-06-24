# PRD: <Phase> — <Feature Name>

> **Template version**: 1.0
> **Use this for every new feature.**

---

## 0. Status

| Field | Value |
|---|---|
| Phase | <e.g., 2b> |
| Status | <PLANNED / IN_PROGRESS / DONE / SUPERSEDED> |
| Patch | <e.g., Patch 8> |
| Source code location | <e.g., packages/ai/resume_tailor.py> |
| Acceptance criteria met | <e.g., 7/10> |
| Last updated | <date> |

---

## 1. Problem Statement

What problem does this solve? Be specific.

---

## 2. User Story

As a <role>, when <event>, I want <action> so that <outcome>.

---

## 3. Goals & Non-Goals

### Goals
- ✅ ...
- ✅ ...

### Non-Goals (explicit)
- ❌ ...
- ❌ ...

---

## 4. Tech Spec

### Files added
- `packages/...`
- ...

### Files modified
- `apps/...`
- `config.yaml` (new keys: ...)
- ...

### Data model changes
- New table / new column: ...

### Config changes
```yaml
# config.yaml
ai:
  <new_keys>: <values>
```

### Dependencies (new packages)
- `pip install <package>`

---

## 5. Step-by-Step Implementation

1. Read [02_ARCHITECTURE.md](../02_ARCHITECTURE.md) for system layout.
2. Read [05_PLUGIN_SPEC.md](../05_PLUGIN_SPEC.md) if touching extractor.
3. Read [ANTI_BREAKAGE_RULES.md](../ANTI_BREAKAGE_RULES.md).
4. Implement file(s):
   ```python
   # code outline or pseudocode
   ```
5. Integrate in `apps/worker/runner.py` or relevant file.
6. Add config keys with defaults.
7. Add logging.
8. Test manually in `safe_auto` mode.

---

## 6. Anti-Hallucination Guards (if AI involved)

Per [20_ANTI_HALLUCINATION.md](../20_ANTI_HALLUCINATION.md), apply these layers:
- [ ] Layer 1: Strict system prompt
- [ ] Layer 2: Format enforcement
- [ ] Layer 3: Option validation
- [ ] Layer 4: UNKNOWN escape hatch
- [ ] Layer 5: Post-validation
- [ ] Layer 6: Diff verification (if applicable)
- [ ] Layer 7: Audit trail
- [ ] Layer 8: First-N manual review

---

## 7. Implementation Checklist

### Build
- [ ] Files created/modified
- [ ] Config keys added
- [ ] Logging added
- [ ] Documentation updated

### Verify (manual)
- [ ] Test on safe_auto mode
- [ ] Verify acceptance test (section 8)
- [ ] No regressions in existing features
- [ ] Backup folder created
- [ ] Patch ZIP created in `patch/job-hunter-pro-patchN/`

### Document
- [ ] `17_CHANGELOG.md` updated
- [ ] `PATCH_HISTORY_LEDGER.md` updated
- [ ] This PRD marked DONE
- [ ] Committed to GitLab

---

## 8. Acceptance Tests

Test must pass for feature to be marked DONE:

- [ ] Given X, when Y, then Z
- [ ] ...

---

## 9. Log Patterns (for observability)

Bot should log:
- `<emoji> <action>` for visual scan

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ... | ... |

---

## 11. Rollback Plan

If patch breaks production:
1. Stop bot
2. Restore from `.backup_pN_<ts>/`
3. Restart

---

## 12. Cross-References

- Architecture: [02_ARCHITECTURE.md](../02_ARCHITECTURE.md)
- Roadmap: [12_PHASE_ROADMAP.md](../12_PHASE_ROADMAP.md)
- Anti-hallucination: [20_ANTI_HALLUCINATION.md](../20_ANTI_HALLUCINATION.md)
- Prompts: [08_PROMPTS_LIBRARY.md](../08_PROMPTS_LIBRARY.md)
- Plugin spec: [05_PLUGIN_SPEC.md](../05_PLUGIN_SPEC.md)
