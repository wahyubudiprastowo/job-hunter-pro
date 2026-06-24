"""
Main bot orchestrator — PATCH 8 (with AI resume tailoring).

NEW vs PATCH 6:
- Loads CV text once at startup, cached
- If ai.resume_tailoring enabled → generates custom resume per job
- Resume passed to apply() is the tailored one (falls back to base)
- Faster startup (skip redundant checks)
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
    from packages.extractors.indeed import IndeedExtractor
    _HAS_INDEED = True
except ImportError:
    IndeedExtractor = None
    _HAS_INDEED = False

try:
    from packages.ai.provider import AIProvider
    from packages.ai.cv_extractor import extract_cv_text
    from packages.ai.resume_tailor import generate_tailored_resume
    from packages.ai.cover_letter import generate_cover_letter
    from packages.ai.scorer import calculate_fit_score, log_fit_score
    _HAS_AI = True
except ImportError:
    AIProvider = None
    extract_cv_text = None
    generate_tailored_resume = None
    generate_cover_letter = None
    calculate_fit_score = None
    log_fit_score = None
    _HAS_AI = False

try:
    from packages.extractors.rate_limiter import SmartRateLimiter, detect_rate_limit_in_driver
    _HAS_RATE_LIMITER = True
except ImportError:
    SmartRateLimiter = None
    detect_rate_limit_in_driver = None
    _HAS_RATE_LIMITER = False

try:
    from packages.stealth.captcha_solver import CaptchaSolver
    _HAS_CAPTCHA_SOLVER = True
except ImportError:
    CaptchaSolver = None
    _HAS_CAPTCHA_SOLVER = False

try:
    from packages.core.orchestrator import HybridOrchestrator
    _HAS_ORCHESTRATOR = True
except ImportError:
    HybridOrchestrator = None
    _HAS_ORCHESTRATOR = False

try:
    from apps.worker.control_platforms import (
        set_platform_state, clear_platform_states,
        get_session_platforms, clear_session_override,
    )
    _HAS_PLATFORM_CONTROL = True
except ImportError:
    set_platform_state = lambda *a, **k: None
    clear_platform_states = lambda: None
    get_session_platforms = lambda: None
    clear_session_override = lambda: None
    _HAS_PLATFORM_CONTROL = False

try:
    from packages.notifications import NotificationCategory, NotificationLevel, NotificationManager
    from packages.notifications.manager import notify
    _HAS_NOTIFICATIONS = True
except ImportError:
    NotificationCategory = None
    NotificationLevel = None
    NotificationManager = None
    _HAS_NOTIFICATIONS = False

    def notify(*args, **kwargs):
        return None

from apps.worker.control import controller

EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
}

if _HAS_INDEED:
    EXTRACTOR_REGISTRY["indeed"] = IndeedExtractor


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _heartbeat_thread(stop_event: threading.Event):
    while not stop_event.is_set():
        controller.beat()
        time.sleep(5)


def _validate_ai_config(ai_cfg: dict) -> tuple[bool, str]:
    if not ai_cfg.get("enabled"):
        return False, "AI disabled in config"
    base_url = (os.getenv("AI_BASE_URL") or ai_cfg.get("base_url", "")).strip()
    if not base_url.startswith(("http://", "https://")):
        return False, f"❌ AI_BASE_URL invalid: '{base_url}'. Must start with http(s)://"
    return True, "AI config OK"


def _resolve_browser_profile(session_platforms: list[str] | None) -> tuple[str, str | None]:
    """
    Resolve browser profile path for the current run.

    If exactly one platform is selected, allow a platform-specific Chrome profile
    so cached login sessions can be reused without affecting other platforms.
    """
    default_user_data_dir = os.getenv("USER_DATA_DIR", "./.chrome-profile")
    default_profile_dir = (os.getenv("CHROME_PROFILE_DIRECTORY") or "").strip() or None

    if not session_platforms or len(session_platforms) != 1:
        return default_user_data_dir, default_profile_dir

    platform = session_platforms[0].strip().upper()
    platform_user_data_dir = (os.getenv(f"{platform}_USER_DATA_DIR") or "").strip()
    platform_profile_dir = (os.getenv(f"{platform}_CHROME_PROFILE_DIRECTORY") or "").strip()

    return (
        platform_user_data_dir or default_user_data_dir,
        platform_profile_dir or default_profile_dir,
    )


def run_bot(config_path: str = "config.yaml"):
    load_dotenv()
    store.init_db()
    config = load_config(config_path)
    orchestration_cfg = config.get("orchestration", {}) or {}

    session = get_session_platforms()
    session_platforms = session.get("platforms") if session else None
    clear_platform_states()

    answers = load_answers()
    profile = CandidateProfile(**config["personal"])
    mode = config.get("mode", "semi_auto")
    stealth_cfg = config["stealth"]
    global_limits_cfg = config.get("global_limits", {}) or {}
    run_cap = int(global_limits_cfg.get("total_apply_per_run", 20))
    ai_cfg = config.get("ai", {}) or {}
    captcha_cfg = config.get("captcha", {}) or {}
    notif_manager = None

    Path("data/logs").mkdir(parents=True, exist_ok=True)
    logger.add("data/logs/bot.log", rotation="5 MB",
               level=os.getenv("LOG_LEVEL", "INFO"))

    if _HAS_NOTIFICATIONS and NotificationManager:
        try:
            notif_manager = NotificationManager.from_config(config, db_path=str(store.DB_PATH))
        except Exception as e:
            logger.warning(f"Notification manager init failed: {e}")

    # Keep the pre-start state written by the web controller so the dashboard
    # does not briefly fall back to IDLE while the worker thread boots.
    controller.clear_command()
    controller.set_state("running")
    controller.beat()

    def _cleanup():
        logger.info("🧹 Cleanup: clearing state files")
        controller.reset()
    atexit.register(_cleanup)

    hb_stop = threading.Event()
    hb_thread = threading.Thread(target=_heartbeat_thread, args=(hb_stop,), daemon=True)
    hb_thread.start()

    # === Load CV (once) ===
    cv_text = None
    resume_path = config["resume"]["default_path"]
    if _HAS_AI and extract_cv_text:
        cv_text = extract_cv_text(resume_path)
        if cv_text:
            logger.success(f"📄 Loaded CV: {len(cv_text)} chars from {resume_path}")
        else:
            logger.warning(f"⚠️  Could not extract CV. AI uses config facts only.")

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
                    ai_provider = None
                else:
                    ok, msg = ai_provider.test_connection()
                    if ok:
                        logger.success(f"🧠 AI: {msg}")
                    else:
                        logger.error(f"❌ AI test FAILED: {msg}")
                        ai_provider = None
            except Exception as e:
                logger.warning(f"AI init failed: {e}")
                ai_provider = None

    tailoring_enabled = bool(ai_cfg.get("resume_tailoring", False) and ai_provider and cv_text)
    if tailoring_enabled:
        logger.success("🎨 Resume tailoring ENABLED — will generate custom resume per job")

    fit_scoring_enabled = bool(
        ai_cfg.get("fit_scoring", False) and ai_provider and cv_text and calculate_fit_score
    )
    fit_threshold = int(ai_cfg.get("fit_threshold", 60))
    if fit_scoring_enabled:
        logger.success(f"🎯 Fit scoring ENABLED — threshold: {fit_threshold}")

    captcha_solver = None
    if _HAS_CAPTCHA_SOLVER and CaptchaSolver:
        try:
            captcha_solver = CaptchaSolver(captcha_cfg, db_path=str(store.DB_PATH))
            if captcha_solver.enabled:
                logger.info(f"CAPTCHA solver enabled: provider={captcha_solver.provider}")
        except Exception as e:
            logger.warning(f"CAPTCHA solver init failed: {e}")
            captcha_solver = None

    browser_user_data_dir, browser_profile_dir = _resolve_browser_profile(session_platforms)

    driver = build_driver(
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        user_data_dir=browser_user_data_dir,
        version_main=int(os.getenv("CHROME_VERSION_MAIN") or 0) or None,
        profile_directory=browser_profile_dir,
    )

    run_id = store.start_run()
    counters = {
        "applied": 0,
        "skipped": 0,
        "failed": 0,
        "needs": 0,
        "tailored": 0,
        "cover_letters_generated": 0,
        "cover_letters_uploaded": 0,
        "fit_scored": 0,
        "fit_skipped": 0,
        "cap_reached": 0,
        "rate_limit_detected": 0,
    }

    def _sync_run_progress():
        store.update_run_progress(
            run_id,
            counters["applied"],
            counters["skipped"],
            counters["failed"],
            counters["needs"],
        )

    current_platform_name = None
    current_platform_applied = 0
    current_platform_skipped = 0

    try:
        for platform_name, pcfg in config["platforms"].items():
            current_platform_name = platform_name
            if session_platforms:
                if platform_name not in session_platforms:
                    continue
            elif not pcfg.get("enabled"):
                continue

            platform_applied = 0
            platform_skipped = 0
            platform_final_state = "idle"
            platform_final_extra = {}
            extractor = None
            current_platform_applied = 0
            current_platform_skipped = 0

            set_platform_state(platform_name, "running", {
                "started_at": int(time.time()),
                "applied": 0,
                "skipped": 0,
            })

            if platform_name not in EXTRACTOR_REGISTRY:
                platform_final_state = "error"
                platform_final_extra = {"error_message": "extractor not available"}
                set_platform_state(platform_name, platform_final_state, {
                    "applied": platform_applied,
                    "skipped": platform_skipped,
                    "finished_at": int(time.time()),
                    **platform_final_extra,
                })
                continue

            extractor_cls = EXTRACTOR_REGISTRY[platform_name]
            try:
                extractor = extractor_cls(
                    driver, pcfg, profile, answers, stealth_cfg,
                    ai_provider=ai_provider, ai_config=ai_cfg, cv_text=cv_text,
                    captcha_solver=captcha_solver,
                )
            except TypeError:
                try:
                    extractor = extractor_cls(
                        driver, pcfg, profile, answers, stealth_cfg,
                        ai_provider=ai_provider, ai_config=ai_cfg,
                    )
                except TypeError:
                    extractor = extractor_cls(driver, pcfg, profile, answers, stealth_cfg)

            email = (os.getenv(f"{platform_name.upper()}_EMAIL") or "").strip()
            password = (os.getenv(f"{platform_name.upper()}_PASSWORD") or "").strip()
            totp = os.getenv(f"{platform_name.upper()}_TOTP_SECRET", "")
            if not email or not password:
                logger.warning(
                    f"Credentials incomplete for {platform_name} - trying existing browser session."
                )

            try:
                extractor.login(email, password, totp)
            except Exception as e:
                logger.error(f"Login failed: {e}")
                platform_final_state = "error"
                platform_final_extra = {"error_message": f"login failed: {e}"}
                set_platform_state(platform_name, platform_final_state, {
                    "applied": platform_applied,
                    "skipped": platform_skipped,
                    "finished_at": int(time.time()),
                    **platform_final_extra,
                })
                try:
                    extractor.close()
                except Exception:
                    pass
                continue

            limiter = None
            if _HAS_RATE_LIMITER and SmartRateLimiter:
                try:
                    limiter = SmartRateLimiter(store.DB_PATH, platform_name, global_limits_cfg)
                    limiter_status = limiter.get_status()
                    if limiter_status.is_blocked:
                        logger.warning(
                            f"Rate limiter blocks {platform_name} - "
                            f"{limiter_status.cooldown_remaining_hours}h remaining"
                        )
                        platform_final_state = "paused"
                        platform_final_extra = {
                            "note": "rate limit active",
                            "cooldown_remaining_hours": limiter_status.cooldown_remaining_hours,
                        }
                        set_platform_state(platform_name, platform_final_state, {
                            "applied": platform_applied,
                            "skipped": platform_skipped,
                            "finished_at": int(time.time()),
                            **platform_final_extra,
                        })
                        try:
                            extractor.close()
                        except Exception:
                            pass
                        continue
                    if limiter_status.is_at_cap:
                        logger.warning(
                            f"Daily cap already reached for {platform_name} "
                            f"({limiter_status.count_today}/{limiter_status.cap_today})"
                        )
                        platform_final_state = "paused"
                        platform_final_extra = {"note": "daily cap reached"}
                        set_platform_state(platform_name, platform_final_state, {
                            "applied": platform_applied,
                            "skipped": platform_skipped,
                            "finished_at": int(time.time()),
                            **platform_final_extra,
                        })
                        try:
                            extractor.close()
                        except Exception:
                            pass
                        continue
                    logger.info(
                        f"Rate limiter ready for {platform_name}: "
                        f"{limiter_status.count_today}/{limiter_status.cap_today} today"
                    )
                except Exception as e:
                    logger.warning(f"Rate limiter init failed for {platform_name}: {e}")
                    limiter = None

            search_cfg = pcfg["search"]
            stop_platform_processing = False
            for query in search_cfg["queries"]:
                if stop_platform_processing or counters["applied"] >= run_cap:
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
                    if counters["applied"] >= run_cap:
                        break
                    controller.check()
                    job_id = card["job_id"]

                    ok, reason = company_passes(card["company"],
                        config["filters"]["company_blacklist"])
                    if not ok:
                        _record_skip(card, platform_name, SkipReason.BLACKLISTED_COMPANY, reason)
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    ok, reason = title_passes(card["title"],
                        config["filters"]["title_keywords_include"],
                        config["filters"]["title_keywords_exclude"])
                    if not ok:
                        _record_skip(card, platform_name, SkipReason.BLACKLISTED_TITLE, reason)
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    if config["filters"]["skip_already_applied"] and store.already_applied(job_id):
                        _record_skip(card, platform_name, SkipReason.DUPLICATE, "already applied")
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue

                    try:
                        job = extractor.open_job_detail(card)
                    except Exception as e:
                        logger.exception(f"open_job_detail: {e}")
                        counters["failed"] += 1
                        _sync_run_progress()
                        continue

                    ok, reason = description_passes(job.description,
                        config["filters"]["description_keywords_exclude"])
                    if not ok:
                        _record_skip_full(job, SkipReason.EXCLUDED_KEYWORD, reason)
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    ok, reason = salary_passes(job.salary, config["filters"]["min_salary"])
                    if not ok:
                        _record_skip_full(job, SkipReason.SALARY_TOO_LOW, reason)
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    if job.raw.get("already_applied"):
                        _record_skip_full(job, SkipReason.DUPLICATE, "already applied on LinkedIn")
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    if not extractor.can_auto_apply(job):
                        _record_skip_full(
                            job,
                            SkipReason.NOT_EASY_APPLY,
                            "external apply",
                            status=ApplyStatus.EXTERNAL,
                        )
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue

                    if limiter:
                        should_block, reason = limiter.should_block()
                        if should_block:
                            _record_skip_full(
                                job,
                                SkipReason.DAILY_CAP_REACHED,
                                f"rate limiter: {reason}",
                            )
                            counters["cap_reached"] += 1
                            counters["skipped"] += 1
                            platform_skipped += 1
                            _sync_run_progress()
                            logger.warning(f"Daily cap reached for {platform_name} - stopping run gracefully")
                            platform_final_state = "paused"
                            platform_final_extra = {"note": reason}
                            stop_platform_processing = True
                            break

                    # === FIT SCORING ===
                    fit_score_result = None
                    if fit_scoring_enabled and job.description:
                        try:
                            fit_score_result = calculate_fit_score(
                                ai_provider,
                                cv_text,
                                job,
                                cache_dir=ai_cfg.get("fit_score_output_dir", "data/fit_scores"),
                            )
                            if fit_score_result:
                                counters["fit_scored"] += 1
                                log_fit_score(fit_score_result, job, job_id=job.job_id)
                                if fit_score_result.score < fit_threshold:
                                    _record_skip_full(
                                        job,
                                        SkipReason.FIT_SCORE_LOW,
                                        f"fit score {fit_score_result.score} < threshold {fit_threshold}",
                                        fit_score=fit_score_result.score,
                                        fit_reasoning=fit_score_result.reasoning,
                                    )
                                    counters["fit_skipped"] += 1
                                    counters["skipped"] += 1
                                    platform_skipped += 1
                                    _sync_run_progress()
                                    continue
                        except Exception as e:
                            logger.warning(f"Fit scoring failed: {e}")

                    # === RESUME TAILORING ===
                    effective_resume = resume_path
                    cover_letter_paths = None
                    if tailoring_enabled and job.description:
                        try:
                            tailored = generate_tailored_resume(
                                ai_provider, profile, cv_text, job,
                                output_dir=ai_cfg.get("resume_output_dir", "resumes/generated")
                            )
                            if tailored:
                                effective_resume = tailored
                                counters["tailored"] += 1
                        except Exception as e:
                            logger.warning(f"Resume tailoring failed: {e}")

                    cover_letter_enabled = bool(
                        ai_cfg.get("cover_letter", False) and ai_provider and cv_text and job.description
                    )
                    if cover_letter_enabled and generate_cover_letter:
                        try:
                            generated = generate_cover_letter(
                                ai_provider,
                                profile,
                                cv_text,
                                job,
                                output_dir=ai_cfg.get("cover_letter_output_dir", "cover_letters/generated"),
                                validator_strict=ai_cfg.get("cover_letter_strict", True),
                            )
                            if generated:
                                txt_path, pdf_path = generated
                                cover_letter_paths = {"txt": txt_path, "pdf": pdf_path}
                                counters["cover_letters_generated"] += 1
                        except Exception as e:
                            logger.warning(f"Cover letter generation failed: {e}")

                    try:
                        result = extractor.apply(
                            job,
                            effective_resume,
                            mode=mode,
                            cover_letter_paths=cover_letter_paths,
                        )
                    except Exception as e:
                        logger.exception(f"apply crashed: {e}")
                        result = ApplicationResult(
                            status=ApplyStatus.FAILED, error_message=str(e))

                    store.record_application(
                        job,
                        result,
                        resume_path=effective_resume,
                        cover_letter_path=result.cover_letter_path,
                        fit_score=fit_score_result.score if fit_score_result else None,
                        fit_reasoning=fit_score_result.reasoning if fit_score_result else None,
                    )

                    if result.status == ApplyStatus.APPLIED:
                        counters["applied"] += 1
                        platform_applied += 1
                        current_platform_applied = platform_applied
                        if limiter:
                            limiter.increment()
                        if result.cover_letter_path:
                            counters["cover_letters_uploaded"] += 1
                        set_platform_state(platform_name, "running", {
                            "started_at": int(time.time()),
                            "applied": platform_applied,
                            "skipped": platform_skipped,
                            "current_job": f"{job.title} @ {job.company}",
                        })
                        suffix = " (tailored)" if effective_resume != resume_path else ""
                        logger.success(f"✅ APPLIED{suffix} [{job.title} @ {job.company}]")
                    elif result.status == ApplyStatus.SKIPPED:
                        counters["skipped"] += 1
                        platform_skipped += 1
                        current_platform_skipped = platform_skipped
                        logger.debug(
                            f"⏭️  Apply returned SKIPPED — check if double-count: {result.error_message}"
                        )
                    elif result.status == ApplyStatus.NEEDS_ANSWERS:
                        counters["needs"] += 1
                        add_unanswered(result.unanswered_questions)
                    else:
                        counters["failed"] += 1
                        add_unanswered(result.unanswered_questions)

                    _sync_run_progress()

                    if limiter and detect_rate_limit_in_driver:
                        matched_phrase = detect_rate_limit_in_driver(driver)
                        if matched_phrase:
                            limiter.record_warning(matched_phrase)
                            counters["rate_limit_detected"] += 1
                            logger.warning(
                                f"Rate limit detected for {platform_name} - stopping run after current record"
                            )
                            platform_final_state = "paused"
                            platform_final_extra = {"note": matched_phrase}
                            stop_platform_processing = True
                            break

                    if counters["applied"] and counters["applied"] % stealth_cfg["pause_every_n_applications"] == 0:
                        logger.info(f"😴 Pause {stealth_cfg['pause_seconds']}s")
                        time.sleep(stealth_cfg["pause_seconds"])
                    human_sleep(stealth_cfg["min_delay_sec"], stealth_cfg["max_delay_sec"])

                if stop_platform_processing:
                    break

            try:
                extractor.close()
            except Exception:
                pass

            set_platform_state(platform_name, platform_final_state, {
                "applied": platform_applied,
                "skipped": platform_skipped,
                "finished_at": int(time.time()),
                **platform_final_extra,
            })

        logger.info(f"🎉 Run done. Counters: {counters}")
    except Exception as e:
        if current_platform_name:
            set_platform_state(current_platform_name, "error", {
                "applied": current_platform_applied,
                "skipped": current_platform_skipped,
                "finished_at": int(time.time()),
                "error_message": str(e),
            })
        logger.exception(f"Run crashed: {e}")
    finally:
        store.finish_run(run_id, counters["applied"], counters["skipped"],
                         counters["failed"], counters["needs"])
        hb_stop.set()
        controller.set_state("idle")
        controller.clear_command()
        clear_session_override()
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass


def _record_skip(card, platform, reason, detail, **extra):
    from packages.core.models import JobListing
    job = JobListing(
        platform=platform, job_id=card["job_id"],
        title=card.get("title", ""), company=card.get("company", ""),
        location=card.get("location", ""),
    )
    result = ApplicationResult(
        status=ApplyStatus.SKIPPED, skip_reason=reason, error_message=detail)
    store.record_application(job, result, **extra)
    logger.info(f"⏭️  SKIP [{card.get('title')} @ {card.get('company')}]: {detail}")


def _record_skip_full(job, reason, detail, status=ApplyStatus.SKIPPED, **extra):
    result = ApplicationResult(
        status=status, skip_reason=reason, error_message=detail)
    store.record_application(job, result, **extra)
    logger.info(f"⏭️  SKIP [{job.title} @ {job.company}]: {detail}")


if __name__ == "__main__":
    run_bot()
