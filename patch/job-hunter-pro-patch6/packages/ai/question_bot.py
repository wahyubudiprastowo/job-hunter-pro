"""
AI question fallback — PATCH 6 (CV-enriched).

When the answer bank misses, AI is called with:
1. Candidate config facts
2. FULL CV PDF text (authoritative source for tech/skills/years)
3. Previously answered Q/A pairs (for consistency)
"""
from __future__ import annotations
import re
from typing import Optional
from loguru import logger
from packages.ai.provider import AIProvider


DEFAULT_SYSTEM_PROMPT = """You are a precise, honest job-application screener-question assistant.

CRITICAL RULES:
- Use ONLY facts from the CANDIDATE FACTS below (including the CV content).
- For "years of experience with X" questions:
  * Read the CV carefully to find when the candidate started using X
  * Calculate years from CV mentions
  * If X is NOT mentioned in CV → answer "0"
  * NEVER invent years
- Numeric Q: ONLY a number (e.g., "8", "0", "3")
- Yes/No Q: ONLY "Yes"/"No" (or local equivalent: "Sì"/"No", "Sí"/"No", "Oui"/"Non", "Ja"/"Nein")
- Multi-choice: ONLY the exact option text from the provided list
- Diversity/EEOC (gender, race, disability, veteran): always "Decline to self-identify"
- Language proficiency: English = "Professional" if CV shows English work; other languages = "Elementary" unless CV shows fluency
- If truly unknown → "UNKNOWN"
- NEVER add explanations, greetings, or extra text
- Output ONLY the answer

CANDIDATE FACTS:
{candidate_facts}
"""


def build_candidate_facts(profile, answer_bank: dict, cv_text: str = None) -> str:
    """
    Build facts including CV text. Imported here for backward compat
    but cv_extractor.build_enriched_facts is preferred.
    """
    from packages.ai.cv_extractor import build_enriched_facts
    return build_enriched_facts(profile, answer_bank, cv_text)


def answer_question_with_ai(
    ai: AIProvider,
    question: str,
    candidate_facts: str,
    field_type: str = "text",
    options: list = None,
    system_prompt_template: str = None,
) -> Optional[str]:
    if not ai.is_available() or not question:
        return None

    options = options or []
    sys_prompt = (system_prompt_template or DEFAULT_SYSTEM_PROMPT).format(
        candidate_facts=candidate_facts
    )

    user_parts = [f"QUESTION: {question}", f"FIELD TYPE: {field_type}"]
    if options:
        opts_str = "\n".join(f"  - {o}" for o in options
                             if o and o.strip() and o != "(no label)")
        user_parts.append(f"AVAILABLE OPTIONS:\n{opts_str}")
    user_parts.append("\nProvide ONLY the answer text, nothing else.")
    user = "\n".join(user_parts)

    raw = ai.chat(sys_prompt, user, max_tokens=80)
    if not raw:
        return None

    answer = _clean_answer(raw)
    if answer.upper() == "UNKNOWN" or not answer:
        logger.info(f"🤖 AI says UNKNOWN for: {question[:60]}")
        return None

    # For multi-choice, ensure answer matches one option
    if options:
        from rapidfuzz import fuzz
        best_opt, best_score = None, 0
        for opt in options:
            if not opt or opt == "(no label)":
                continue
            if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                return opt
            s = fuzz.partial_ratio(answer.lower(), opt.lower())
            if s > best_score:
                best_opt, best_score = opt, s
        if best_opt and best_score >= 70:
            logger.info(f"🤖 AI '{answer}' → option '{best_opt}' ({best_score})")
            return best_opt
        logger.warning(f"🤖 AI answer '{answer}' didn't match options for: {question[:60]}")
        return None

    logger.info(f"🤖 AI answered '{answer}' for: {question[:60]}")
    return answer


def _clean_answer(raw: str) -> str:
    a = raw.strip()
    for prefix in ["answer:", "a:", "response:", "the answer is:"]:
        if a.lower().startswith(prefix):
            a = a[len(prefix):].strip()
    a = a.strip('"\'`')
    a = a.rstrip(".")
    a = re.sub(r"\*+", "", a)
    return a.strip()
