"""
AI question fallback.

When the answer bank + fuzzy match fails, call AI to answer a screener question
using ONLY the candidate's known facts. Anti-hallucination guard: AI must
answer in strict format; we parse and validate.
"""
from __future__ import annotations
import json
import re
from typing import Optional
from loguru import logger
from packages.ai.provider import AIProvider


DEFAULT_SYSTEM_PROMPT = """You are a job application screener-question answering assistant. Your job:
- Answer screener questions HONESTLY based on the candidate's facts below.
- For numeric questions (years of experience, salary), respond with ONLY a number.
- For Yes/No questions, respond with ONLY "Yes" or "No".
- For multiple-choice, respond with ONLY the exact option text from the list.
- For diversity/EEOC questions (gender, race, disability, veteran), respond with "Decline to self-identify".
- If you genuinely cannot answer from the candidate's facts, respond with the literal word: UNKNOWN
- DO NOT invent skills, certifications, or experience the candidate doesn't have.
- DO NOT add explanations, greetings, or extra text — output ONLY the answer.

CANDIDATE FACTS:
{candidate_facts}
"""


def build_candidate_facts(profile, answer_bank: dict) -> str:
    """Build a structured fact sheet for the AI."""
    p = profile
    facts = [
        f"- Name: {p.first_name} {p.last_name}",
        f"- Email: {p.email}",
        f"- Phone: {p.phone_country_code} {p.phone}",
        f"- Location: {p.city}, {p.country}",
        f"- Current company: {p.current_company}",
        f"- Current title: {p.current_title}",
        f"- Total years of experience: {p.years_experience}",
        f"- Highest education: {p.highest_education}",
        f"- Authorized to work: {p.authorized_to_work}",
        f"- Requires sponsorship: {p.require_sponsorship}",
        f"- Willing to relocate: {p.willing_to_relocate}",
        f"- Notice period (days): {p.notice_period_days}",
        f"- Expected salary: {p.expected_salary}",
        f"- Current salary: {p.current_salary}",
    ]
    if p.linkedin_url:
        facts.append(f"- LinkedIn: {p.linkedin_url}")
    if p.github_url:
        facts.append(f"- GitHub: {p.github_url}")

    # Add answer bank as known Q/A pairs
    if answer_bank:
        facts.append("\n# Previously answered questions:")
        for q, a in list(answer_bank.items())[:30]:  # cap to avoid prompt bloat
            facts.append(f'- "{q}" -> "{a}"')

    return "\n".join(facts)


def answer_question_with_ai(
    ai: AIProvider,
    question: str,
    candidate_facts: str,
    field_type: str = "text",
    options: list = None,
    system_prompt_template: str = None,
) -> Optional[str]:
    """
    Call AI to answer one screener question.
    Returns the answer string, or None if AI says UNKNOWN / unavailable / invalid.
    """
    if not ai.is_available() or not question:
        return None

    options = options or []
    sys_prompt = (system_prompt_template or DEFAULT_SYSTEM_PROMPT).format(
        candidate_facts=candidate_facts
    )

    user_parts = [f"QUESTION: {question}"]
    user_parts.append(f"FIELD TYPE: {field_type}")
    if options:
        opts_str = "\n".join(f"  - {o}" for o in options if o and o.strip() and o != "(no label)")
        user_parts.append(f"AVAILABLE OPTIONS:\n{opts_str}")
    user_parts.append("\nProvide ONLY the answer text, nothing else.")
    user = "\n".join(user_parts)

    raw = ai.chat(sys_prompt, user, max_tokens=80)
    if not raw:
        return None

    answer = _clean_answer(raw)

    if answer.upper() == "UNKNOWN" or not answer:
        logger.info(f"🤖 AI replied UNKNOWN for: {question[:60]}")
        return None

    # For multi-choice, ensure answer matches one of the options (fuzzy)
    if options:
        from rapidfuzz import fuzz
        best_opt, best_score = None, 0
        for opt in options:
            if not opt or opt == "(no label)":
                continue
            # Exact substring or fuzzy
            if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                return opt
            s = fuzz.partial_ratio(answer.lower(), opt.lower())
            if s > best_score:
                best_opt, best_score = opt, s
        if best_opt and best_score >= 70:
            logger.info(f"🤖 AI '{answer}' matched option '{best_opt}' ({best_score})")
            return best_opt
        logger.warning(f"🤖 AI answer '{answer}' didn't match any option for: {question[:60]}")
        return None

    logger.info(f"🤖 AI answered '{answer}' for: {question[:60]}")
    return answer


def _clean_answer(raw: str) -> str:
    """Strip quotes, markdown, prefixes like 'Answer:' from AI response."""
    a = raw.strip()
    # Remove common prefixes
    for prefix in ["answer:", "a:", "response:", "the answer is:"]:
        if a.lower().startswith(prefix):
            a = a[len(prefix):].strip()
    # Strip quotes
    a = a.strip('"\'`')
    # Remove trailing punctuation if alone
    a = a.rstrip(".")
    # Remove markdown bold/italic
    a = re.sub(r"\*+", "", a)
    return a.strip()
