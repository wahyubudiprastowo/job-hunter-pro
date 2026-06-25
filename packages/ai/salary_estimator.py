"""
AI salary estimator for discovery jobs that do not expose compensation.

This is a best-effort market estimate, not an official salary from the post.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from loguru import logger


SALARY_ESTIMATION_PROMPT = """You estimate likely annual compensation ranges for job opportunities.

Rules:
- Use the job title, company, location, and description to infer a realistic market salary range.
- Be conservative. Do not invent extreme ranges.
- Prefer annual gross salary.
- Include currency in the output.
- If the location strongly implies a market, use that local market.
- If information is insufficient, return UNKNOWN.

OUTPUT FORMAT (strict JSON only):
{{
  "salary_text": "<short salary range like '$120k-$150k/year' or 'UNKNOWN'>",
  "confidence": "low" | "medium" | "high",
  "reasoning": "<one short sentence>"
}}

JOB TITLE: {job_title}
COMPANY: {company}
LOCATION: {location}
JOB DESCRIPTION:
{job_description}
"""


def estimate_salary_range(ai, job, cache_dir: str = "data/salary_estimates") -> Optional[str]:
    if not ai or not ai.is_available():
        return None
    if not (job.title or "").strip():
        return None

    cache_path = Path(cache_dir) / f"{job.job_id}.json"
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            salary_text = _normalize_salary_text(data.get("salary_text"))
            if salary_text:
                logger.debug(f"Reusing cached salary estimate for {job.job_id}: {salary_text}")
                return salary_text
        except Exception as e:
            logger.debug(f"Salary estimate cache read failed: {e}")

    try:
        prompt = SALARY_ESTIMATION_PROMPT.format(
            job_title=job.title or "",
            company=job.company or "",
            location=job.location or "",
            job_description=(job.description or "")[:2500],
        )
    except Exception as e:
        logger.warning(f"Salary estimate prompt failed: {e}")
        return None

    raw = ai.chat(
        system=prompt,
        user="Return the JSON salary estimate now.",
        max_tokens=220,
    )
    if not raw:
        return None

    parsed = _parse_response(raw)
    if not parsed:
        logger.warning(f"Could not parse salary estimate response: {raw[:200]}")
        return None

    salary_text = _normalize_salary_text(parsed.get("salary_text"))
    if not salary_text:
        return None

    final_text = f"Est. {salary_text}"
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "salary_text": final_text,
                    "confidence": parsed.get("confidence", ""),
                    "reasoning": parsed.get("reasoning", ""),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug(f"Salary estimate cache write failed: {e}")

    return final_text


def _parse_response(raw: str) -> Optional[dict]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_salary_text(value) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.upper() == "UNKNOWN":
        return None
    return text
