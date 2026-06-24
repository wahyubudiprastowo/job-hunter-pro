"""
Main bot orchestrator — PATCH 6.

NEW vs PATCH 5:
- Reads CV PDF at startup via packages.ai.cv_extractor
- Passes cv_text to extractor for AI-enriched facts
- Better config validation (warn if base_url looks invalid)
"""
from __future__ import annotations
import os
import time
import atexit
import threading
import yaml
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

from packages.stealth.browser import build_driver
from packages.stealth.humanizer import human_sleep
from packages.core.models import (
    SearchFilters, CandidateProfile, ApplicationResult, ApplyStatus, SkipReason
)
from packages.core.filters import (
    title_passes, description_passes, company_passes, salary_passes
)
from packages.storage import db as store
from packages.storage.answers import (
    load_answers, save_answers, add_unanswered
)
from packages.extractors.linkedin import LinkedInExtractor

try:
    from packages.ai.provider import AIProvider
    from packages.ai.cv_extractor import extract_cv_text
    _HAS_AI = True
except ImportError:
    AIProvider = None
    extract_cv_text = None
    _HAS_AI = False

from apps.worker.control import controller

EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
}


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _heartbeat_thread(stop_event: threading.Event):
    while not stop_event.is_set():
        controller.beat()
        time.sleep(5)


def _validate_ai_config(ai_cfg: dict) -> tuple[bool, str]:
    """Sanity-check AI config. Returns (ok, message)."""
    if not ai_cfg.get("enabled"):
        return False, "AI disabled in config"
    base_url = (os.getenv("AI_BASE_URL") or ai_cfg.get("base_url", "")).strip()
    if not base_url.startswith(("http://", "https://")):
        return False, (
            f"❌ AI_BASE_URL looks invalid: '{base_url}'. "
            "Must start with http:// or https://. Check your .env file."
        )
    return True, "AI config OK"


def run_bot(config_path: str = "config.yaml"):
    load_dotenv()
    store.init_db()
    config = load_config(config_path)

    answers = load_answers()
    profile = CandidateProfile(**config["personal"])
    mode = config.get("mode", "semi_auto")
    stealth_cfg = config["stealth"]
    daily_cap = config["global_limits"]["total_apply_per_run"]
    ai_cfg = config.get("ai", {}) or {}

    Path("data/logs").mkdir(parents=True, exist_ok=True)
    logger.add("data/logs/bot.log", rotation="5 MB",
               level=os.getenv("LOG_LEVEL", "INFO"))

    controller.reset()
    controller.set_state("running")
    controller.beat()

    def _cleanup():
        logger.info("🧹 Cleanup: clearing state files")
        controller.reset()
    atexit.register(_cleanup)

    hb_stop = threading.Event()
    hb_thread = threading.Thread(target=_heartbeat_thread, args=(hb_stop,), daemon=True)
    hb_thread.start()

    # === Load CV text ===
    cv_text = None
    resume_path = config["resume"]["default_path"]
    if _HAS_AI and extract_cv_text:
        cv_text = extract_cv_text(resume_path)
        if cv_text:
            logger.success(f"📄 Loaded CV: {len(cv_text)} chars from {resume_path}")
        else:
            logger.warning(f"⚠️  Could not extract CV from {resume_path}. "
                           "AI will work with config facts only.")

    # === AI provider ===
    ai_provider = None
    if _HAS_AI and ai_cfg.get("enabled", False):
        ok, msg = _validate_ai_config(ai_cfg)
        if not ok:
            logger.error(msg)
        else:
            try:
                ai_provider = AIProvider(ai_cfg)
                if not ai_provider.is_available():
                    logger.warning("AI configured but not available.")
                    ai_provider = None
                else:
                    ok, msg = ai_provider.test_connection()
                    if ok:
                        logger.success(f"🧠 AI connection test: {msg}")
                    else:
                        logger.error(f"❌ AI connection test FAILED: {msg}")
                        logger.warning("Bot will continue WITHOUT AI fallback.")
                        ai_provider = None
            except Exception as e:
                logger.warning(f"AI provider init failed: {e}")
                ai_provider = None

    driver = build_driver(
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        user_data_dir=os.getenv("USER_DATA_DIR", "./.chrome-profile"),
        version_main=int(os.getenv("CHROME_VERSION_MAIN") or 0) or None,
    )

    run_id = store.start_run()
    counters = {"applied": 0, "skipped": 0, "failed": 0, "needs": 0}

    try:
        for platform_name, pcfg in config["platforms"].items():
            if not pcfg.get("enabled"):
                continue
            if platform_name not in EXTRACTOR_REGISTRY:
                continue

            extractor_cls = EXTRACTOR_REGISTRY[platform_name]
            try:
                extractor = extractor_cls(
                    driver, pcfg, profile, answers, stealth_cfg,
                    ai_provider=ai_provider, ai_config=ai_cfg, cv_text=cv_text,
                )
            except TypeError:
                # Backward compat: try without cv_text
                try:
                    extractor = extractor_cls(
                        driver, pcfg, profile, answers, stealth_cfg,
                        ai_provider=ai_provider, ai_config=ai_cfg,
                    )
                except TypeError:
                    extractor = extractor_cls(driver, pcfg, profile, answers, stealth_cfg)

            email = os.getenv(f"{platform_name.upper()}_EMAIL")
            password = os.getenv(f"{platform_name.upper()}_PASSWORD")
            totp = os.getenv(f"{platform_name.upper()}_TOTP_SECRET", "")
            if not email or not password:
                logger.error(f"Missing credentials for {platform_name}.")
                continue

            try:
                extractor.login(email, password, totp)
            except Exception as e:
                logger.error(f"Login failed for {platform_name}: {e}")
                continue

            search_cfg = pcfg["search"]
            for query in search_cfg["queries"]:
                if counters["applied"] >= daily_cap:
                    break
                controller.check()
                filters = SearchFilters(
                    queries=[query], location=search_cfg["location"],
                    remote=search_cfg.get("remote", False),
                    hybrid=search_cfg.get("hybrid", False),
                    date_posted=search_cfg["date_posted"],
                    experience_levels=search_cfg.get("experience_levels", []),
                    job_type=search_cfg.get("job_type", "Full-time"),
                    easy_apply_only=search_cfg.get("easy_apply_only", True),
                )
                extractor.search(filters)
                cards = extractor.collect_job_cards(
                    max_cards=pcfg["max_apply_per_run"] * 3)

                for card in cards:
                    if counters["applied"] >= daily_cap:
                        break
                    controller.check()
                    job_id = card["job_id"]

                    ok, reason = company_passes(card["company"],
                        config["filters"]["company_blacklist"])
                    if not ok:
                        _record_skip(card, platform_name, SkipReason.BLACKLISTED_COMPANY, reason)
                        counters["skipped"] += 1; continue
                    ok, reason = title_passes(card["title"],
                        config["filters"]["title_keywords_include"],
                        config["filters"]["title_keywords_exclude"])
                    if not ok:
                        _record_skip(card, platform_name, SkipReason.BLACKLISTED_TITLE, reason)
                        counters["skipped"] += 1; continue
                    if config["filters"]["skip_already_applied"] and store.already_applied(job_id):
                        _record_skip(card, platform_name, SkipReason.DUPLICATE, "already applied")
                        counters["skipped"] += 1; continue

                    try:
                        job = extractor.open_job_detail(card)
                    except Exception as e:
                        logger.exception(f"open_job_detail: {e}")
                        counters["failed"] += 1; continue

                    ok, reason = description_passes(job.description,
                        config["filters"]["description_keywords_exclude"])
                    if not ok:
                        _record_skip_full(job, SkipReason.EXCLUDED_KEYWORD, reason)
                        counters["skipped"] += 1; continue
                    ok, reason = salary_passes(job.salary, config["filters"]["min_salary"])
                    if not ok:
                        _record_skip_full(job, SkipReason.SALARY_TOO_LOW, reason)
                        counters["skipped"] += 1; continue
                    if not extractor.can_auto_apply(job):
                        _record_skip_full(job, SkipReason.NOT_EASY_APPLY, "external apply")
                        counters["skipped"] += 1; continue

                    try:
                        result = extractor.apply(job, resume_path, mode=mode)
                    except Exception as e:
                        logger.exception(f"apply crashed: {e}")
                        result = ApplicationResult(
                            status=ApplyStatus.FAILED, error_message=str(e))

                    store.record_application(job, result, resume_path=resume_path)

                    if result.status == ApplyStatus.APPLIED:
                        counters["applied"] += 1
                        logger.success(f"✅ APPLIED [{job.title} @ {job.company}]")
                    elif result.status == ApplyStatus.SKIPPED:
                        counters["skipped"] += 1
                    elif result.status == ApplyStatus.NEEDS_ANSWERS:
                        counters["needs"] += 1
                        add_unanswered(result.unanswered_questions)
                    else:
                        counters["failed"] += 1
                        add_unanswered(result.unanswered_questions)

                    if counters["applied"] and counters["applied"] % stealth_cfg["pause_every_n_applications"] == 0:
                        logger.info(f"😴 Pause {stealth_cfg['pause_seconds']}s")
                        time.sleep(stealth_cfg["pause_seconds"])
                    human_sleep(stealth_cfg["min_delay_sec"], stealth_cfg["max_delay_sec"])

            try:
                extractor.close()
            except Exception:
                pass

        logger.info(f"🎉 Run done. Counters: {counters}")
    except Exception as e:
        logger.exception(f"Run crashed: {e}")
    finally:
        store.finish_run(run_id, counters["applied"], counters["skipped"],
                         counters["failed"], counters["needs"])
        hb_stop.set()
        controller.set_state("idle")
        controller.clear_command()
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass


def _record_skip(card, platform, reason, detail):
    from packages.core.models import JobListing
    job = JobListing(
        platform=platform, job_id=card["job_id"],
        title=card.get("title", ""), company=card.get("company", ""),
        location=card.get("location", ""),
    )
    result = ApplicationResult(
        status=ApplyStatus.SKIPPED, skip_reason=reason, error_message=detail)
    store.record_application(job, result)
    logger.info(f"⏭️  SKIP [{card.get('title')} @ {card.get('company')}]: {detail}")


def _record_skip_full(job, reason, detail):
    result = ApplicationResult(
        status=ApplyStatus.SKIPPED, skip_reason=reason, error_message=detail)
    store.record_application(job, result)
    logger.info(f"⏭️  SKIP [{job.title} @ {job.company}]: {detail}")


if __name__ == "__main__":
    run_bot()
