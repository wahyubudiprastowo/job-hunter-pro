"""
Job Fit Scorer (Phase 2d, Patch 17).

Scores job fit on 0-100 scale before resume tailoring.
Uses cache per job_id to avoid repeated AI cost.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger


SCORE_SYSTEM_PROMPT = """You are an expert career advisor analyzing job fit.

Your task: given a candidate's CV and a job description, score the fit on a
scale of 0-100 and provide reasoning.

CRITICAL RULES:
- Be conservative - don't inflate scores
- Score 90-100: PERFECT match (all required skills + experience match)
- Score 70-89: STRONG match (most skills match, minor gaps)
- Score 50-69: AVERAGE match (some skills match, notable gaps)
- Score 30-49: WEAK match (significant gaps, would need stretching)
- Score 0-29: POOR match (very few skills match)

OUTPUT FORMAT (strict JSON, no other text):
{
  "score": <integer 0-100>,
  "matched_skills": [<list of skills present in BOTH CV and JD>],
  "missing_skills": [<list of REQUIRED JD skills NOT in CV>],
  "red_flags": [<list of disqualifiers>],
  "reasoning": "<2-3 sentence explanation>",
  "recommendation": "APPLY" | "SKIP" | "MAYBE"
}

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

JOB TITLE: {job_title}
COMPANY: {company}

Return the JSON only.
"""


@dataclass
class FitScore:
    score: int
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    reasoning: str = ""
    recommendation: str = "MAYBE"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "red_flags": self.red_flags,
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
        }


def calculate_fit_score(ai, cv_text: str, job, cache_dir: str = "data/fit_scores") -> Optional[FitScore]:
    if not ai or not ai.is_available():
        logger.debug("AI not available - skipping fit score")
        return None
    if not cv_text:
        logger.debug("No CV text - skipping fit score")
        return None
    if not job.description:
        logger.debug("No job description - skipping fit score")
        return None

    cache_path = Path(cache_dir) / f"{job.job_id}.json"
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            fit = _fit_from_dict(data)
            if fit:
                logger.debug(f"Reusing cached fit score: {data.get('score')} for {job.job_id}")
                return fit
        except Exception as e:
            logger.debug(f"Fit score cache read failed: {e}")

    try:
        prompt = SCORE_SYSTEM_PROMPT.format(
            cv_text=cv_text[:5000],
            job_description=(job.description or "")[:3000],
            job_title=job.title or "",
            company=job.company or "",
        )
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Scoring prompt format failed: {e}")
        return None

    raw = ai.chat(
        system=prompt,
        user="Return the fit score JSON now.",
        max_tokens=600,
    )
    if not raw:
        logger.warning("AI returned empty for fit scoring")
        return None

    parsed = _parse_score_response(raw)
    if not parsed:
        logger.warning(f"Could not parse fit score response: {raw[:200]}")
        return None

    score = parsed.get("score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        logger.warning(f"Invalid score value: {score}")
        return None

    fit = FitScore(
        score=score,
        matched_skills=_as_str_list(parsed.get("matched_skills")),
        missing_skills=_as_str_list(parsed.get("missing_skills")),
        red_flags=_as_str_list(parsed.get("red_flags")),
        reasoning=str(parsed.get("reasoning", "")).strip(),
        recommendation=str(parsed.get("recommendation", "MAYBE")).strip().upper() or "MAYBE",
    )

    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(fit.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug(f"Fit score cache write failed: {e}")

    return fit


def _parse_score_response(raw: str) -> Optional[dict]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if "score" in data and "reasoning" in data:
            return data
    except json.JSONDecodeError:
        return None
    return None


def _as_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_recommendation(value: str, score: int) -> str:
    rec = str(value or "").strip().upper()
    if rec in {"APPLY", "SKIP", "MAYBE"}:
        return rec
    if score >= 70:
        return "APPLY"
    if score >= 50:
        return "MAYBE"
    return "SKIP"


def _fit_from_dict(data: dict) -> Optional[FitScore]:
    score = data.get("score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        return None

    matched_skills = _as_str_list(data.get("matched_skills"))
    missing_skills = _as_str_list(data.get("missing_skills"))
    red_flags = _as_str_list(data.get("red_flags"))

    matched_lower = {item.lower() for item in matched_skills}
    missing_skills = [item for item in missing_skills if item.lower() not in matched_lower]

    return FitScore(
        score=score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        red_flags=red_flags,
        reasoning=str(data.get("reasoning", "")).strip(),
        recommendation=_normalize_recommendation(data.get("recommendation", "MAYBE"), score),
    )


def log_fit_score(fit: FitScore, job, job_id: str = ""):
    suffix = f" [job={job_id}]" if job_id else ""
    if fit.score >= 80:
        level = "HIGH"
    elif fit.score >= 60:
        level = "MID"
    else:
        level = "LOW"

    logger.info(
        f"Fit score: {fit.score}/100 ({level}){suffix} "
        f"[{job.title} @ {job.company}] -> {fit.recommendation}"
    )
    if fit.missing_skills:
        logger.debug(f"Missing skills: {fit.missing_skills[:5]}")
    if fit.red_flags:
        logger.debug(f"Red flags: {fit.red_flags}")
