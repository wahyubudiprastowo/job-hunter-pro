# 🛡️ Anti-Hallucination (Cross-Cutting)

> **Principle**: The candidate would rather not get an interview than be caught lying.

## What Counts as Hallucination

| Type | Example | Severity |
|---|---|---|
| Inventing tech | Resume says Python; AI adds "Kubernetes" | CRITICAL |
| Inflating years | 3y → "5y" | CRITICAL |
| Fake certifications | Adding never-earned cert | CRITICAL |
| Misrepresenting role | "Senior" when "Mid" | HIGH |
| Embellishing | "Led 20" when 5 | HIGH |
| Inventing companies | New experience entries | CRITICAL |
| Wrong language level | "Fluent German" when basic | HIGH |
| False skill claims | "Yes" to skill candidate lacks | HIGH |

## 8 Safeguard Layers

### Layer 1: Strict System Prompts
Every prompt explicitly forbids invention. See [08_PROMPTS_LIBRARY.md](08_PROMPTS_LIBRARY.md).

### Layer 2: Format Enforcement
- Numeric → ONLY number
- Yes/No → ONLY Yes/No
- Multi-choice → ONLY option
- Reject prose responses

### Layer 3: Option Validation
For multi-choice, fuzzy-match AI answer to actual option (≥70%). Reject if no match.

### Layer 4: UNKNOWN Escape Hatch
AI can say "UNKNOWN" → bot adds to unanswered queue (no fake).

### Layer 5: Post-Validation
- Numeric: ≤ candidate's total
- Boolean: cross-check skill exists
- Tech name: must be in CV

### Layer 6: Diff Verification (Resume Tailoring)
```python
def detect_new_tech(base, tailored):
    base_tech = extract_tech_terms(base)
    tailored_tech = extract_tech_terms(tailored)
    new = tailored_tech - base_tech
    if new: raise HallucinationError(new)
```

### Layer 7: Audit Trail
Every AI call logged: question + response + validation + model + timestamp.

### Layer 8: First-N Manual Review
First 3 generations of new AI feature → UI banner "Please review".

## Per-Use-Case

### Question Answering (P2a) ✅
1, 2, 3, 4, 7 active.

### Resume Tailoring (P2b)
ALL 8 layers, plus:
- Word count ≤ 1.1 × base
- Section structure preserved
- Dates immutable
- Company names immutable
- "Facts you may use" section explicit

### Cover Letter (P2c)
ALL 8 plus:
- Cross-ref claimed skills with resume
- ≤ 300 words
- Must reference JD-specific detail
- Forbidden phrases blocked

### Fit Scoring (P2d)
- Reasoning ≥ 2 sentences
- matched ∩ missing = empty
- Recommendation aligned with score

### Interview Prep (P3c)
- STAR drafts cite specific resume facts
- No generic claims

## When Hallucination Detected
```
AI returns content
   → Validator detects
   → Log warning
   → Don't use output
   → Fallback:
     - Question → unanswered queue
     - Resume → use base
     - Cover letter → don't upload
     - Fit score → MAYBE
   → P5: notify channel
```

## Hallucination Audit
Weekly (P2+):
1. Sample 5 random outputs
2. Compare to source facts
3. Score: Y/N
4. Target: 0%

If > 0%: tighten prompt + add validation layer.

## 🔗 Related
- [07_AI_SPEC.md](07_AI_SPEC.md)
- [08_PROMPTS_LIBRARY.md](08_PROMPTS_LIBRARY.md)
- [01_PROJECT_VISION.md](01_PROJECT_VISION.md)
