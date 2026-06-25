from __future__ import annotations

import yaml
from dotenv import load_dotenv
from types import SimpleNamespace

from packages.ai.provider import AIProvider
from packages.ai.salary_estimator import estimate_salary_range
from packages.storage import discovered_jobs as discovered_store


def main():
    load_dotenv()
    with open("config.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    ai_cfg = config.get("ai", {}) or {}
    if not ai_cfg.get("enabled") or not ai_cfg.get("salary_estimation"):
        print("AI salary estimation is disabled in config.")
        return

    discovered_store.init_schema()
    rows = discovered_store.list_missing_salaries(limit=200)
    if not rows:
        print("No discovered jobs with missing salaries.")
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
            location=row.get("location") or "",
            description=row.get("description") or "",
        )
        salary_text = estimate_salary_range(
            ai,
            job,
            cache_dir=ai_cfg.get("salary_estimation_output_dir", "data/salary_estimates"),
        )
        if not salary_text:
            skipped += 1
            print(f"SKIP {job.title} @ {job.company} - no estimate")
            continue
        discovered_store.update_enrichment(
            int(row["id"]),
            salary=salary_text,
        )
        updated += 1
        print(f"OK {salary_text}  {job.title} @ {job.company}")

    print(f"Done. Updated={updated}, Skipped={skipped}, Total={len(rows)}")


if __name__ == "__main__":
    main()
