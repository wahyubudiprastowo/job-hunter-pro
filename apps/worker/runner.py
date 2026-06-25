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
import json
import time
import atexit
import threading
import re
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
from packages.core.discovery_filter_helper import should_apply_filter
from packages.storage import db as store
from packages.storage import discovered_jobs as discovered_store
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
    from packages.extractors.glassdoor import GlassdoorExtractor
    _HAS_GLASSDOOR = True
except ImportError:
    GlassdoorExtractor = None
    _HAS_GLASSDOOR = False

try:
    from packages.ai.provider import AIProvider
    from packages.ai.cv_extractor import extract_cv_text
    from packages.ai.resume_tailor import generate_tailored_resume
    from packages.ai.cover_letter import generate_cover_letter
    from packages.ai.scorer import calculate_fit_score, log_fit_score
    from packages.ai.salary_estimator import estimate_salary_range
    _HAS_AI = True
except ImportError:
    AIProvider = None
    extract_cv_text = None
    generate_tailored_resume = None
    generate_cover_letter = None
    calculate_fit_score = None
    log_fit_score = None
    estimate_salary_range = None
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
    from apps.web.discovery_trigger import merge_discovery_config, clear_discovery_session
    _HAS_DISCOVERY_TRIGGER = True
except ImportError:
    merge_discovery_config = None
    clear_discovery_session = lambda: None
    _HAS_DISCOVERY_TRIGGER = False

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

try:
    from apps.web.realtime_tracker import get_tracker
    _tracker = get_tracker()
except ImportError:
    _tracker = None

from apps.worker.control import controller

EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
}

if _HAS_INDEED:
    EXTRACTOR_REGISTRY["indeed"] = IndeedExtractor
if _HAS_GLASSDOOR:
    EXTRACTOR_REGISTRY["glassdoor"] = GlassdoorExtractor


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _normalize_title_gate_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+/#.-]+", " ", (value or "").lower())).strip()


def _indeed_title_gate(job, query: str, config: dict) -> tuple[bool, str]:
    title_gate_cfg = (((config.get("platforms", {}) or {}).get("indeed", {}) or {}).get("title_gate", {}) or {})
    if not title_gate_cfg.get("enabled", False):
        return True, ""

    normalized_title = _normalize_title_gate_text(getattr(job, "title", "") or "")
    normalized_query = _normalize_title_gate_text(query or "")
    if not normalized_title:
        return False, "indeed title gate: empty title"

    negative_hints = [
        _normalize_title_gate_text(item)
        for item in title_gate_cfg.get("negative_hints", [])
        if _normalize_title_gate_text(item)
    ]
    for hint in negative_hints:
        if hint in normalized_title:
            return False, f"indeed title gate: matched negative hint '{hint}'"

    positive_hints = [
        _normalize_title_gate_text(item)
        for item in title_gate_cfg.get("positive_hints", [])
        if _normalize_title_gate_text(item)
    ]

    query_tokens = [
        token for token in normalized_query.split()
        if token not in {"engineer", "senior", "lead", "remote", "hybrid"}
    ]
    query_matched = any(token and token in normalized_title for token in query_tokens)
    positive_matched = any(hint in normalized_title for hint in positive_hints)

    if query_matched or positive_matched:
        return True, ""
    return False, "indeed title gate: title does not match cloud/devops hints"


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

    # If a platform-specific profile folder exists but env still points to the
    # shared default profile, prefer the dedicated one to preserve login state.
    conventional_platform_dir = f"./.chrome-profile-{platform.lower()}"
    if (
        platform_user_data_dir in ("", default_user_data_dir)
        and Path(conventional_platform_dir).exists()
    ):
        platform_user_data_dir = conventional_platform_dir

    return (
        platform_user_data_dir or default_user_data_dir,
        platform_profile_dir or default_profile_dir,
    )


def _load_apply_queue(path: str = "data/.control/apply_queue.json") -> list[dict]:
    queue_path = Path(path)
    if not queue_path.exists():
        return []
    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict)]
    except Exception as e:
        logger.warning(f"Could not read apply queue: {e}")
        return []


def _load_due_discovered_queue(limit: int = 200) -> list[dict]:
    now_ts = int(time.time())
    rows = discovered_store.list_discovered(
        status=discovered_store.STATUS_AUTO_APPLY,
        limit=limit,
    )
    due_rows = []
    for row in rows:
        scheduled_at = row.get("scheduled_at")
        if scheduled_at and int(scheduled_at) > now_ts:
            continue
        due_rows.append({
            "discovered_id": row.get("id"),
            "platform": row.get("platform"),
            "job_id": row.get("job_id"),
            "title": row.get("title"),
            "company": row.get("company"),
            "location": row.get("location"),
            "url": row.get("url"),
            "fit_score": row.get("fit_score"),
            "fit_reasoning": row.get("fit_reasoning"),
        })
    return due_rows


def run_bot(config_path: str = "config.yaml"):
    load_dotenv()
    store.init_db()
    discovered_store.init_schema()
    config = load_config(config_path)
    if _HAS_DISCOVERY_TRIGGER and merge_discovery_config:
        config = merge_discovery_config(config)
    orchestration_cfg = config.get("orchestration", {}) or {}
    discovery_cfg = config.get("discovery", {}) or {}

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
    discovery_mode = bool(discovery_cfg.get("enabled", False))
    apply_queue_items = _load_apply_queue()
    if not apply_queue_items and not discovery_mode:
        apply_queue_items = _load_due_discovered_queue()
    if apply_queue_items:
        discovery_mode = False
        run_cap = max(run_cap, len(apply_queue_items))
        logger.info(f"Queued apply mode enabled for {len(apply_queue_items)} discovered job(s)")
    if discovery_mode:
        logger.info("Discovery mode enabled: scrape and curate only, no apply")
        cleanup_days = int(discovery_cfg.get("cleanup_after_days", 30) or 30)
        if cleanup_days > 0:
            discovered_store.cleanup_old(cleanup_days)
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
    if _tracker:
        _tracker.reset(keep_logs=False)
        _tracker.set_state("running")
        _tracker.set_run_progress(0, run_cap)
        _tracker.set_run_counters(0, 0, 0, 0)
        _tracker.add_activity("Bot started", "info")
        _tracker.add_log("Bot started.")

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

    salary_estimation_enabled = bool(
        ai_cfg.get("salary_estimation", False) and ai_provider and estimate_salary_range
    )
    if salary_estimation_enabled:
        logger.success("💰 Salary estimation ENABLED for jobs with missing salary")

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
        "discovered": 0,
        "tailored": 0,
        "cover_letters_generated": 0,
        "cover_letters_uploaded": 0,
        "fit_scored": 0,
        "fit_skipped": 0,
        "auto_apply_queued": 0,
        "cap_reached": 0,
        "rate_limit_detected": 0,
    }

    notify(
        notif_manager,
        title="Bot started",
        message="Job-Hunter Pro run started.",
        level=NotificationLevel.INFO if NotificationLevel else None,
        category=NotificationCategory.BOT_STATE if NotificationCategory else None,
        metadata={
            "mode": mode,
            "platforms": ",".join(session_platforms or []),
            "run_cap": run_cap,
        },
    )

    def _sync_run_progress():
        store.update_run_progress(
            run_id,
            counters["applied"],
            counters["skipped"],
            counters["failed"],
            counters["needs"],
        )
        if _tracker:
            _tracker.set_run_progress(counters["applied"], run_cap)
            _tracker.set_run_counters(
                counters["applied"],
                counters["skipped"],
                counters["failed"],
                counters["needs"],
            )

    current_platform_name = None
    current_platform_applied = 0
    current_platform_skipped = 0
    apply_queue_consumed = False

    def _mark_discovered_result(queue_item: dict | None, result: ApplicationResult | None = None, *, skipped: bool = False, failed: bool = False, note: str = ""):
        if not queue_item or not queue_item.get("discovered_id"):
            return
        discovered_id = int(queue_item["discovered_id"])
        if result and result.status == ApplyStatus.APPLIED:
            discovered_store.update_status([discovered_id], discovered_store.STATUS_APPLIED, notes=note)
            return
        if result and result.status == ApplyStatus.FAILED:
            discovered_store.update_status([discovered_id], discovered_store.STATUS_FAILED, notes=note or (result.error_message or ""))
            return
        if failed:
            discovered_store.update_status([discovered_id], discovered_store.STATUS_FAILED, notes=note)
            return
        if skipped or (result and result.status in (ApplyStatus.SKIPPED, ApplyStatus.EXTERNAL)):
            discovered_store.update_status([discovered_id], discovered_store.STATUS_SKIPPED, notes=note or (result.error_message if result else ""))

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
            platform_discovered = 0
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
            if _tracker:
                _tracker.add_activity(f"{platform_name.upper()} started", "info")
                _tracker.add_log(f"{platform_name.upper()}: started.")

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

            if discovery_mode:
                try:
                    extractor.config["scroll_count"] = max(
                        int(extractor.config.get("scroll_count", 8) or 8),
                        int(discovery_cfg.get("scroll_depth", 15) or 15),
                    )
                except Exception:
                    pass

            email = (os.getenv(f"{platform_name.upper()}_EMAIL") or "").strip()
            password = (os.getenv(f"{platform_name.upper()}_PASSWORD") or "").strip()
            totp = os.getenv(f"{platform_name.upper()}_TOTP_SECRET", "")
            if not email or not password:
                logger.warning(
                    f"Credentials incomplete for {platform_name} - trying existing browser session."
                )

            try:
                extractor.login(email, password, totp)
                if _tracker:
                    _tracker.add_activity(f"{platform_name.upper()} session ready", "success")
            except Exception as e:
                logger.error(f"Login failed: {e}")
                if _tracker:
                    _tracker.add_activity(f"{platform_name.upper()} login failed", "error")
                    _tracker.add_log(f"{platform_name.upper()}: login failed - {e}")
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
            queued_cards = []
            if apply_queue_items:
                for item in apply_queue_items:
                    if (item.get("platform") or "").strip().lower() != platform_name:
                        continue
                    queued_cards.append({
                        "job_id": str(item.get("job_id") or "").strip(),
                        "title": item.get("title") or "",
                        "company": item.get("company") or "",
                        "location": item.get("location") or "",
                        "url": item.get("url") or "",
                        "_element": None,
                        "_queue_item": item,
                    })

            stop_platform_processing = False
            query_sequence = ["__apply_queue__"] if queued_cards else search_cfg["queries"]
            if (not queued_cards) and discovery_mode:
                query_limit = int(pcfg.get("query_limit_per_run", 0) or 0)
                if query_limit > 0:
                    query_sequence = query_sequence[:query_limit]
            for query in query_sequence:
                if stop_platform_processing or counters["applied"] >= run_cap:
                    break
                controller.check()
                queue_mode = bool(queued_cards)
                if _tracker:
                    _tracker.set_step("Queued apply" if queue_mode else f"Searching: {query}", 5)
                    _tracker.add_activity(
                        f"{platform_name.upper()} queued apply" if queue_mode else f"{platform_name.upper()} search: {query}",
                        "info",
                    )
                if queue_mode:
                    logger.info(f"Processing {len(queued_cards)} queued discovered job(s) for {platform_name}")
                    cards = queued_cards
                else:
                    filters = SearchFilters(
                        queries=[query], location=search_cfg["location"],
                        remote=search_cfg.get("remote", False),
                        hybrid=search_cfg.get("hybrid", False),
                        date_posted=search_cfg["date_posted"],
                        experience_levels=search_cfg.get("experience_levels", []),
                        job_type=search_cfg.get("job_type", "Full-time"),
                        easy_apply_only=search_cfg.get("easy_apply_only", True),
                    )
                    try:
                        search_ok = extractor.search(filters)
                        if search_ok is False:
                            if getattr(extractor, "pause_current_run", False):
                                note = getattr(extractor, "pause_reason", "platform paused for this run")
                                logger.warning(f"{platform_name} paused for this run: {note}")
                                if _tracker:
                                    _tracker.add_activity(f"{platform_name.upper()} paused", "warning")
                                    _tracker.add_log(f"{platform_name.upper()}: paused - {note}")
                                platform_final_state = "paused"
                                platform_final_extra = {"note": note}
                                stop_platform_processing = True
                                break
                            continue
                        discovery_cap = int(discovery_cfg.get("max_per_session", 100) or 100)
                        platform_discovery_cap = int(
                            pcfg.get("discovery_max_per_session", discovery_cap) or discovery_cap
                        )
                        max_cards = (
                            min(discovery_cap, platform_discovery_cap)
                            if discovery_mode
                            else pcfg["max_apply_per_run"] * 3
                        )
                        cards = extractor.collect_job_cards(max_cards=max_cards)
                        if not cards and getattr(extractor, "pause_current_run", False):
                            note = getattr(extractor, "pause_reason", "platform paused for this run")
                            logger.warning(f"{platform_name} paused for this run: {note}")
                            if _tracker:
                                _tracker.add_activity(f"{platform_name.upper()} paused", "warning")
                                _tracker.add_log(f"{platform_name.upper()}: paused - {note}")
                            platform_final_state = "paused"
                            platform_final_extra = {"note": note}
                            stop_platform_processing = True
                            break
                    except Exception as e:
                        logger.exception(f"{platform_name} search failed for '{query}': {e}")
                        if _tracker:
                            _tracker.add_activity(
                                f"{platform_name.upper()} search failed: {query}",
                                "error",
                            )
                            _tracker.add_log(
                                f"SEARCH_FAILED {platform_name}: {query} - {e}"
                            )
                        continue

                for card in cards:
                    if counters["applied"] >= run_cap:
                        break
                    controller.check()
                    job_id = card["job_id"]
                    queue_item = card.get("_queue_item")
                    if _tracker:
                        _tracker.set_current_job(
                            title=card.get("title", ""),
                            company=card.get("company", ""),
                            platform=platform_name,
                            step="Filtering",
                        )
                        _tracker.set_step("Filtering", 10)

                    if should_apply_filter("company_blacklist", discovery_mode, queue_item):
                        ok, reason = company_passes(card["company"],
                            config["filters"]["company_blacklist"])
                        if not ok:
                            _record_skip(card, platform_name, SkipReason.BLACKLISTED_COMPANY, reason)
                            counters["skipped"] += 1
                            platform_skipped += 1
                            _sync_run_progress()
                            continue
                    if should_apply_filter("title_keywords", discovery_mode, queue_item):
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
                        _mark_discovered_result(queue_item, skipped=True, note="already applied")
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue

                    try:
                        job = extractor.open_job_detail(card)
                        if _tracker:
                            _tracker.set_current_job(
                                title=job.title,
                                company=job.company,
                                platform=platform_name,
                                step="Job detail loaded",
                            )
                            _tracker.set_step("Job detail loaded", 20)
                    except Exception as e:
                        logger.exception(f"open_job_detail: {e}")
                        _mark_discovered_result(queue_item, failed=True, note=f"open_job_detail: {e}")
                        counters["failed"] += 1
                        _sync_run_progress()
                        continue

                    if platform_name == "indeed" and discovery_mode:
                        ok, reason = _indeed_title_gate(job, query, config)
                        if not ok:
                            logger.info(f"Indeed title gate rejected [{job.title} @ {job.company}]: {reason}")
                            counters["skipped"] += 1
                            platform_skipped += 1
                            _sync_run_progress()
                            continue

                    if should_apply_filter("description_keywords_exclude", discovery_mode, queue_item):
                        ok, reason = description_passes(job.description,
                            config["filters"]["description_keywords_exclude"])
                        if not ok:
                            _record_skip_full(job, SkipReason.EXCLUDED_KEYWORD, reason)
                            counters["skipped"] += 1
                            platform_skipped += 1
                            _sync_run_progress()
                            continue
                    if should_apply_filter("min_salary", discovery_mode, queue_item):
                        ok, reason = salary_passes(job.salary, config["filters"]["min_salary"])
                        if not ok:
                            _record_skip_full(job, SkipReason.SALARY_TOO_LOW, reason)
                            counters["skipped"] += 1
                            platform_skipped += 1
                            _sync_run_progress()
                            continue
                    if job.raw.get("already_applied"):
                        _record_skip_full(job, SkipReason.DUPLICATE, "already applied on LinkedIn")
                        _mark_discovered_result(queue_item, skipped=True, note="already applied on platform")
                        counters["skipped"] += 1
                        platform_skipped += 1
                        _sync_run_progress()
                        continue
                    if not discovery_mode and not extractor.can_auto_apply(job):
                        _record_skip_full(
                            job,
                            SkipReason.NOT_EASY_APPLY,
                            "external apply",
                            status=ApplyStatus.EXTERNAL,
                        )
                        _mark_discovered_result(queue_item, skipped=True, note="external apply")
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

                    queued_fit_score = queue_item.get("fit_score") if queue_item else None
                    queued_fit_reasoning = queue_item.get("fit_reasoning") if queue_item else None

                    # === FIT SCORING ===
                    fit_score_result = None
                    if fit_scoring_enabled and job.description and not (queue_item and queued_fit_score is not None):
                        try:
                            if _tracker:
                                _tracker.set_step("Fit scoring", 30)
                            fit_score_result = calculate_fit_score(
                                ai_provider,
                                cv_text,
                                job,
                                cache_dir=ai_cfg.get("fit_score_output_dir", "data/fit_scores"),
                            )
                            if fit_score_result:
                                counters["fit_scored"] += 1
                                log_fit_score(fit_score_result, job, job_id=job.job_id)
                                if _tracker:
                                    _tracker.set_current_job(
                                        title=job.title,
                                        company=job.company,
                                        platform=platform_name,
                                        step="Fit scoring",
                                        fit_score=fit_score_result.score,
                                    )
                                if (not discovery_mode) and (not queue_item) and fit_score_result.score < fit_threshold:
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

                    if discovery_mode:
                        salary_value = job.salary
                        if salary_estimation_enabled and not (salary_value or "").strip():
                            try:
                                salary_estimate = estimate_salary_range(
                                    ai_provider,
                                    job,
                                    cache_dir=ai_cfg.get("salary_estimation_output_dir", "data/salary_estimates"),
                                )
                                if salary_estimate:
                                    salary_value = salary_estimate
                            except Exception as e:
                                logger.warning(f"Salary estimation failed: {e}")
                        discovered_status = discovered_store.STATUS_DISCOVERED
                        auto_threshold = int(discovery_cfg.get("auto_apply_threshold", 90) or 90)
                        auto_skip_threshold = int(discovery_cfg.get("auto_skip_threshold", 30) or 30)
                        score_value = fit_score_result.score if fit_score_result else queued_fit_score
                        reasoning_value = fit_score_result.reasoning if fit_score_result else queued_fit_reasoning
                        if score_value is not None:
                            if score_value >= auto_threshold:
                                discovered_status = discovered_store.STATUS_AUTO_APPLY
                                counters["auto_apply_queued"] += 1
                            elif score_value < auto_skip_threshold:
                                discovered_status = discovered_store.STATUS_SKIPPED
                        discovered_id = discovered_store.save_discovered({
                            "platform": platform_name,
                            "job_id": job.job_id,
                            "title": job.title,
                            "company": job.company,
                            "location": job.location,
                            "url": job.url,
                            "description": job.description,
                            "salary": salary_value,
                            "fit_score": score_value,
                            "fit_reasoning": reasoning_value,
                            "is_easy_apply": job.is_easy_apply,
                            "status": discovered_status,
                            "metadata": {"raw": job.raw or {}},
                        })
                        if discovered_id:
                            counters["discovered"] += 1
                            platform_discovered += 1
                            logger.info(
                                f"Discovered [{job.title} @ {job.company}]"
                                f" status={discovered_status}"
                                f" fit={score_value if score_value is not None else '-'}"
                            )
                        discovery_cap = int(discovery_cfg.get("max_per_session", 100) or 100)
                        platform_discovery_cap = int(
                            pcfg.get("discovery_max_per_session", discovery_cap) or discovery_cap
                        )
                        if counters["discovered"] >= discovery_cap:
                            logger.info(f"Discovery cap reached ({counters['discovered']})")
                            stop_platform_processing = True
                        elif platform_discovered >= platform_discovery_cap:
                            logger.info(
                                f"{platform_name} discovery cap reached "
                                f"({platform_discovered}/{platform_discovery_cap})"
                            )
                            stop_platform_processing = True
                        _sync_run_progress()
                        continue

                    # === RESUME TAILORING ===
                    effective_resume = resume_path
                    cover_letter_paths = None
                    if tailoring_enabled and job.description:
                        try:
                            if _tracker:
                                _tracker.set_step("Resume tailoring", 50)
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
                            if _tracker:
                                _tracker.set_step("Cover letter", 70)
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
                        if _tracker:
                            _tracker.set_step("Applying", 90)
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
                        fit_score=fit_score_result.score if fit_score_result else queued_fit_score,
                        fit_reasoning=fit_score_result.reasoning if fit_score_result else queued_fit_reasoning,
                    )
                    _mark_discovered_result(queue_item, result=result)

                    if result.status == ApplyStatus.APPLIED:
                        counters["applied"] += 1
                        platform_applied += 1
                        current_platform_applied = platform_applied
                        if _tracker:
                            _tracker.set_step("Applied", 100)
                            _tracker.add_activity(f"Applied: {job.title} @ {job.company}", "success")
                            _tracker.add_log(f"APPLIED {platform_name}: {job.title} @ {job.company}")
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
                        notify(
                            notif_manager,
                            title="Application submitted",
                            message=f"{job.title} at {job.company}",
                            level=NotificationLevel.SUCCESS if NotificationLevel else None,
                            category=NotificationCategory.APPLICATION if NotificationCategory else None,
                            metadata={
                                "platform": platform_name,
                                "company": job.company or "",
                                "total_applied": counters["applied"],
                            },
                        )
                        if counters["applied"] and counters["applied"] % 10 == 0:
                            notify(
                                notif_manager,
                                title="Apply milestone",
                                message=f"{counters['applied']} applications submitted in this run.",
                                level=NotificationLevel.INFO if NotificationLevel else None,
                                category=NotificationCategory.DAILY_SUMMARY if NotificationCategory else None,
                                metadata={"run_id": run_id, "applied": counters["applied"]},
                            )
                    elif result.status == ApplyStatus.SKIPPED:
                        counters["skipped"] += 1
                        platform_skipped += 1
                        current_platform_skipped = platform_skipped
                        if _tracker:
                            _tracker.set_step("Skipped", 100)
                        logger.debug(
                            f"⏭️  Apply returned SKIPPED — check if double-count: {result.error_message}"
                        )
                    elif result.status == ApplyStatus.NEEDS_ANSWERS:
                        counters["needs"] += 1
                        if _tracker:
                            _tracker.set_step("Needs answers", 100)
                            _tracker.add_activity(f"Needs answers: {job.title} @ {job.company}", "warning")
                            _tracker.add_log(f"NEEDS_ANSWERS {platform_name}: {job.title}")
                        add_unanswered(result.unanswered_questions)
                    else:
                        counters["failed"] += 1
                        if _tracker:
                            _tracker.set_step("Failed", 100)
                            _tracker.add_activity(f"Failed: {job.title} @ {job.company}", "error")
                            _tracker.add_log(f"FAILED {platform_name}: {job.title} - {result.error_message or 'unknown error'}")
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
                            notify(
                                notif_manager,
                                title="Rate limit detected",
                                message=f"{platform_name} paused after rate limit warning.",
                                level=NotificationLevel.WARNING if NotificationLevel else None,
                                category=NotificationCategory.RATE_LIMIT if NotificationCategory else None,
                                metadata={"platform": platform_name, "reason": matched_phrase},
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

            if platform_final_state == "paused" and platform_final_extra:
                notify(
                    notif_manager,
                    title=f"{platform_name} paused",
                    message=platform_final_extra.get("note", "Platform paused."),
                    level=NotificationLevel.WARNING if NotificationLevel else None,
                    category=NotificationCategory.RATE_LIMIT if NotificationCategory else None,
                    metadata={"platform": platform_name, **platform_final_extra},
                )

        apply_queue_consumed = bool(apply_queue_items)
        logger.info(f"🎉 Run done. Counters: {counters}")
        if _tracker:
            _tracker.add_activity(
                f"Run completed: {counters['applied']} applied, {counters['skipped']} skipped",
                "success",
            )
            _tracker.add_log(
                f"Run completed. Applied={counters['applied']} Skipped={counters['skipped']} Failed={counters['failed']} Needs={counters['needs']}"
            )
        notify(
            notif_manager,
            title="Run completed",
            message="Job-Hunter Pro run finished.",
            level=NotificationLevel.INFO if NotificationLevel else None,
            category=NotificationCategory.DAILY_SUMMARY if NotificationCategory else None,
            metadata={
                "run_id": run_id,
                "applied": counters["applied"],
                "skipped": counters["skipped"],
                "failed": counters["failed"],
                "needs_answers": counters["needs"],
            },
        )
    except Exception as e:
        if current_platform_name:
            set_platform_state(current_platform_name, "error", {
                "applied": current_platform_applied,
                "skipped": current_platform_skipped,
                "finished_at": int(time.time()),
                "error_message": str(e),
            })
        logger.exception(f"Run crashed: {e}")
        if _tracker:
            _tracker.set_state("error")
            _tracker.add_activity(f"Run crashed: {e}", "error")
            _tracker.add_log(f"Run crashed: {e}")
        notify(
            notif_manager,
            title="Run crashed",
            message=str(e),
            level=NotificationLevel.ERROR if NotificationLevel else None,
            category=NotificationCategory.ERROR if NotificationCategory else None,
            metadata={"platform": current_platform_name or "", "run_id": run_id},
        )
    finally:
        store.finish_run(run_id, counters["applied"], counters["skipped"],
                         counters["failed"], counters["needs"])
        if apply_queue_consumed:
            try:
                Path("data/.control/apply_queue.json").unlink(missing_ok=True)
            except Exception:
                pass
        hb_stop.set()
        controller.set_state("idle")
        if _tracker:
            _tracker.set_run_progress(counters["applied"], run_cap)
            _tracker.set_run_counters(
                counters["applied"],
                counters["skipped"],
                counters["failed"],
                counters["needs"],
            )
            _tracker.set_state("idle")
            _tracker.add_activity("Bot stopped", "info")
            _tracker.add_log("Bot stopped.")
        controller.clear_command()
        clear_session_override()
        clear_discovery_session()
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
        url=card.get("url", ""),
    )
    result = ApplicationResult(
        status=ApplyStatus.SKIPPED, skip_reason=reason, error_message=detail)
    store.record_application(job, result, **extra)
    logger.info(f"⏭️  SKIP [{card.get('title')} @ {card.get('company')}]: {detail}")
    if _tracker:
        _tracker.add_activity(f"Skipped: {card.get('title')} @ {card.get('company')}", "warning")
        _tracker.add_log(f"SKIP {platform}: {card.get('title')} - {detail}")


def _record_skip_full(job, reason, detail, status=ApplyStatus.SKIPPED, **extra):
    result = ApplicationResult(
        status=status, skip_reason=reason, error_message=detail)
    store.record_application(job, result, **extra)
    logger.info(f"⏭️  SKIP [{job.title} @ {job.company}]: {detail}")
    if _tracker:
        level = "warning" if status in (ApplyStatus.SKIPPED, ApplyStatus.EXTERNAL) else "error"
        _tracker.add_activity(f"{status.value.title()}: {job.title} @ {job.company}", level)
        _tracker.add_log(f"{status.value.upper()} {job.platform}: {job.title} - {detail}")


if __name__ == "__main__":
    run_bot()
