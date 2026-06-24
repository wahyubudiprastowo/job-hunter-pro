# 🧠 AI Specification

## Provider Abstraction
`packages/ai/provider.py::AIProvider`:
- OpenAI-compatible (works with OpenAI, OmniRouter, Ollama, DeepSeek, etc.)
- Retry + cooldown on failure
- Graceful degradation

## Configuration
```yaml
ai:
  enabled: true
  question_fallback: true           # ✅ Phase 2a
  resume_tailoring: true            # 🟡 Phase 2b (currently false in prod)
  cover_letter: false               # ⏭️ Phase 2c
  fit_scoring: false                # ⏭️ Phase 2d
  fit_threshold: 60
  auto_save_answers: true
  model: "gpt-4o-mini"
  base_url: ""                       # empty = OpenAI default
  temperature: 0.2
  timeout_seconds: 60
  max_retries: 1
  retry_backoff_sec: 3
  failure_cooldown_seconds: 300
  system_prompt: |
    [custom prompt — see docs/08]
```

## Failure Handling
```
chat() called
 → attempt 1
   ↓ exception?
   yes → wait backoff → attempt 2
         ↓ still fail?
         yes → cooldown 300s → return None
```

## Cost Per Use
| Use | Tokens | Cost (gpt-4o-mini) |
|---|---|---|
| Question | ~80 | $0.0001 |
| Resume tailor | ~1500 | $0.001 |
| Cover letter | ~600 | $0.0004 |
| Fit score | ~300 | $0.0002 |

Daily: ~$0.05 with gpt-4o-mini for 25 applies.

## Caching
- Answer bank IS the question cache
- Resume cached by job_id
- Cover letter cached by company
- Fit score cached by job_id

## Anti-Hallucination
See [20_ANTI_HALLUCINATION.md](20_ANTI_HALLUCINATION.md) — 8 layers.

## 🔗 Related
- [08_PROMPTS_LIBRARY.md](08_PROMPTS_LIBRARY.md)
- [PRDs/PRD_2a..2d](PRDs/INDEX.md)
