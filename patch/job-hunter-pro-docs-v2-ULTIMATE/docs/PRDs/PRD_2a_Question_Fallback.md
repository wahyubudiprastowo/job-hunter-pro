# PRD: Phase 2a — AI Question Fallback

## 0. Status
| Field | Value |
|---|---|
| Phase | 2a |
| Status | ✅ DONE |
| Patch | Patch 3 |
| Source code | `packages/ai/{provider,question_bot}.py` |
| Acceptance | 6/6 ✅ |
| Last verified | 2026-06-24 (121 saved answers growing) |

## 1. Problem Statement
LinkedIn forms in EU have screener questions in 7+ languages. Static answer bank misses ~80% of them on first encounter. Manual filling each one breaks automation.

## 2. User Story
As a candidate, when bot hits an unknown screener question (any language), I want AI to answer honestly using my facts, AND save it so next time it's free + instant.

## 3. Goals & Non-Goals
### Goals
- ✅ Answer screener questions in any language
- ✅ Use OpenAI-compatible providers (OpenAI, OmniRouter, Ollama, DeepSeek)
- ✅ Auto-save answers — bot learns
- ✅ Anti-hallucination guards
- ✅ Graceful degradation (works if AI down)

### Non-Goals
- ❌ Invent skills/experience
- ❌ Be smarter than the candidate
- ❌ Replace user judgment on tricky questions

## 4. Tech Spec
### Files
- `packages/ai/__init__.py` (new)
- `packages/ai/provider.py` (new) — AIProvider class
- `packages/ai/question_bot.py` (new) — answer_question_with_ai
- `packages/extractors/linkedin.py` (modified) — step 6 in `_lookup_answer`
- `apps/worker/runner.py` (modified) — instantiate AIProvider
- `config.yaml` (new keys) — `ai.*` block

### Config
```yaml
ai:
  enabled: true
  question_fallback: true
  auto_save_answers: true
  model: "gpt-4o-mini"
  base_url: ""
  temperature: 0.2
  failure_cooldown_seconds: 300
  system_prompt: |
    [strict prompt — see docs/08]
```

### .env
```
AI_API_KEY=<key>
AI_BASE_URL=<endpoint>
```

## 5. Step-by-Step Implementation
1. Add `openai>=1.50.0` to requirements
2. Create `provider.py` with retry + cooldown
3. Create `question_bot.py` with strict prompt + UNKNOWN escape
4. Add step 6 in `_lookup_answer`: AI fallback after bank misses
5. On success, auto-save to `data/answers.json`
6. Wire AIProvider in runner.py
7. Test on Italian/German form

## 6. Anti-Hallucination Guards
- ✅ Layer 1: System prompt forbids invention
- ✅ Layer 2: Format enforcement (number / Yes-No / option)
- ✅ Layer 3: Fuzzy validation ≥70% for multi-choice
- ✅ Layer 4: UNKNOWN escape hatch
- ✅ Layer 7: Audit log (every call)

## 7. Implementation Checklist
- [x] All files created
- [x] Config block added
- [x] AI provider initializes
- [x] Bot works with AI disabled
- [x] Bot works with AI down (cooldown)
- [x] Auto-save persists
- [x] Tested on Italian form (SORINT.lab)
- [x] No hallucinations observed

## 8. Acceptance Tests
- [x] AI initializes — log shows "AI provider ready"
- [x] AI called when bank misses — log shows 🤖
- [x] AI answer saved — log shows 💾
- [x] `data/answers.json` grows after run
- [x] Cooldown triggers on persistent failure
- [x] Bot works with `ai.enabled: false`

## 9. Log Patterns
```
INFO | 🧠 AI provider ready: model=..., base_url=...
INFO | 🤖 AI answered '<answer>' for: <question>
INFO | 💾 Saved AI answer: '<q>' -> '<a>'
INFO | 🤖 AI replied UNKNOWN for: <q>
WARNING | AI provider failing — cooldown 300s
```

## 10. Risks
| Risk | Mitigation |
|---|---|
| AI hallucinates | 8 safeguard layers + audit |
| AI endpoint down | 300s cooldown, fallback to unanswered queue |
| Bot crashes from AI | Graceful try/except in question_bot |

## 11. Rollback
Restore `.backup_p3_*/`.

## 12. Cross-Refs
- [08_PROMPTS_LIBRARY.md](../08_PROMPTS_LIBRARY.md) `question.v1`
- [07_AI_SPEC.md](../07_AI_SPEC.md)
- [20_ANTI_HALLUCINATION.md](../20_ANTI_HALLUCINATION.md)
