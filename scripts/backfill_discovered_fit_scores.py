from __future__ import annotations

import os
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv

from packages.ai.cv_extractor import extract_cv_text
from packages.ai.provider import AIProvider
from packages.ai.scorer import calculate_fit_score
from packages.storage import discovered_jobs as discovered_store


def main():
    load_dotenv()
    with open("config.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    ai_cfg = config.get("ai", {}) or {}
    if not ai_cfg.get("enabled") or not ai_cfg.get("fit_scoring"):
        print("AI fit scoring is disabled in config.")
        return

    discovered_store.init_schema()
    rows = discovered_store.list_missing_fit_scores(limit=200)
    if not rows:
        print("No discovered jobs with missing fit scores.")
        return

    resume_path = config.get("resume", {}).get("default_path", "")
    cv_text = extract_cv_text(resume_path)
    if not cv_text:
        print(f"Could not extract CV text from: {resume_path}")
        return

    ai = AIProvider(ai_cfg)
    if not ai.is_available():
        print("AI provider is not available.")
        return

    updated = 0
    skipped = 0
    for row in rows:
        job = SimpleNamespace(
            job_id=str(row.get("job_id") or ""),
            title=row.get("title") or "",
            company=row.get("company") or "",
            description=row.get("description") or "",
        )
        fit = calculate_fit_score(
            ai,
            cv_text,
            job,
            cache_dir=ai_cfg.get("fit_score_output_dir", "data/fit_scores"),
        )
        if not fit:
            skipped += 1
            print(f"SKIP {job.title} @ {job.company} - no score")
            continue
        discovered_store.update_enrichment(
            int(row["id"]),
            fit_score=fit.score,
            fit_reasoning=fit.reasoning,
        )
        updated += 1
        print(f"OK {fit.score:>3}  {job.title} @ {job.company}")

    print(f"Done. Updated={updated}, Skipped={skipped}, Total={len(rows)}")


if __name__ == "__main__":
    main()
