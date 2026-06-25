"""Flask dashboard — PATCH 5: + Reset button + AI test + diagnostics."""
import os
import json
import csv
import io
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, Response
)
from dotenv import load_dotenv

from packages.storage import db as store
from packages.storage import discovered_jobs as discovered_store
from packages.storage.answers import (
    load_answers, save_answers, load_unanswered, clear_unanswered,
    resolve_unanswered,
)
from packages.extractors.rate_limiter import get_status_for_dashboard, SmartRateLimiter
from apps.worker.control import controller
from apps.worker.control_platforms import (
    get_all_platform_states,
    set_session_platforms,
    get_session_platforms,
    clear_session_override,
    set_preferred_platforms,
    get_preferred_platforms,
    clear_preferred_platforms,
)
from apps.worker.runner import run_bot
from apps.web.discovery_trigger import (
    set_discovery_session,
    get_discovery_session,
)
from packages.stealth.profile_manager import (
    list_all_profiles,
    reset_profile,
    cleanup_old_backups,
    get_profile_history,
)
from apps.web.settings_api import (
    load_config as settings_load_config,
    save_config as settings_save_config,
    update_config_section,
    load_env,
    save_env,
    get_env_for_display,
    validate_config,
)
from apps.web.realtime_tracker import get_tracker

try:
    from packages.notifications import NotificationManager
    _HAS_NOTIFICATIONS = True
except ImportError:
    NotificationManager = None
    _HAS_NOTIFICATIONS = False

load_dotenv()
store.init_db()
discovered_store.init_schema()

app = Flask(__name__,
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

_runner_thread = None


def _format_local_datetime(value):
    """Convert stored UTC-naive timestamps into local server time for the UI."""
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value).replace("T", " ")[:19]


def _format_local_unix(value):
    if value in (None, ""):
        return ""
    try:
        return _format_local_datetime(datetime.fromtimestamp(int(value), tz=timezone.utc))
    except Exception:
        return str(value)


app.jinja_env.filters["localdt"] = _format_local_datetime
app.jinja_env.filters["localunix"] = _format_local_unix


@app.context_processor
def _inject_layout_state():
    unanswered = load_unanswered()
    discovered_stats = discovered_store.get_stats()
    discovered_badge = (
        discovered_stats.get("by_status", {}).get("discovered", 0)
        + discovered_stats.get("by_status", {}).get("selected", 0)
        + discovered_stats.get("by_status", {}).get("auto_apply", 0)
        + discovered_stats.get("by_status", {}).get("saved", 0)
    )
    return {
        "state": controller.get_state(),
        "stats": store.get_stats(),
        "unanswered_count": len(unanswered),
        "discovered_count": discovered_badge,
    }


def _latest_debug_screenshot():
    shots_dir = Path("data/screenshots")
    if not shots_dir.exists():
        return None
    files = [p for p in shots_dir.glob("*.png") if p.is_file()]
    if not files:
        return None
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return {
        "name": latest.name,
        "path": str(latest),
        "modified_at": _format_local_datetime(datetime.fromtimestamp(latest.stat().st_mtime)),
    }


def _load_config_file() -> tuple[dict, str | None]:
    try:
        import yaml
        cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8")) or {}
        return cfg, None
    except Exception as e:
        return {}, f"{type(e).__name__}: {e}"


def _parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("\r", "").replace("\n", ",").split(",") if item.strip()]


def _load_global_limits_config() -> dict:
    cfg, _ = _load_config_file()
    try:
        return cfg.get("global_limits", {}) or {}
    except Exception:
        return {}


def _load_platform_config_summary(cfg: dict | None = None) -> list[dict]:
    cfg = cfg or {}
    result = []
    for name, pcfg in (cfg.get("platforms", {}) or {}).items():
        result.append({
            "name": name,
            "enabled": bool(pcfg.get("enabled", False)),
            "max_apply": int(pcfg.get("max_apply_per_run", 0) or 0),
            "credentials_ready": _platform_credentials_ready(name),
        })
    return result


def _platform_credentials_ready(platform_name: str) -> bool:
    load_dotenv()
    return bool(
        (os.getenv(f"{platform_name.upper()}_EMAIL") or "").strip()
        and (os.getenv(f"{platform_name.upper()}_PASSWORD") or "").strip()
    )


def _missing_credentials(platforms: list[str]) -> list[str]:
    return [platform for platform in platforms if not _platform_credentials_ready(platform)]


def _get_platform_states_for_dashboard(platforms: list[dict] | None = None) -> dict:
    platforms = platforms or _load_platform_config_summary()
    raw_states = get_all_platform_states()
    controller_state = controller.get_state()
    merged = {}
    for platform in platforms:
        name = platform["name"]
        state_info = dict(raw_states.get(name, {"platform": name, "state": "idle"}))
        if controller_state not in ("running", "paused") and state_info.get("state") in ("running", "paused"):
            state_info["state"] = "idle"
        merged[name] = state_info
    for name, state in raw_states.items():
        if name not in merged:
            state_info = dict(state)
            if controller_state not in ("running", "paused") and state_info.get("state") in ("running", "paused"):
                state_info["state"] = "idle"
            merged[name] = state_info
    return merged


def _rate_limit_status(platform: str = "linkedin"):
    try:
        return get_status_for_dashboard(store.DB_PATH, platform, _load_global_limits_config())
    except Exception:
        return None


def _rate_limit_statuses(platforms: list[dict] | None = None) -> list[dict]:
    platforms = platforms or _load_platform_config_summary()
    names = [p["name"] for p in platforms if p.get("enabled")]
    if not names:
        names = ["linkedin"]
    statuses = []
    for name in names:
        status = _rate_limit_status(name)
        if status:
            statuses.append(status)
    return statuses


def _get_stats_today() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    result = {"applied": 0, "skipped": 0}
    with sqlite3.connect(store.DB_PATH) as conn:
        applied = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='applied' AND DATE(created_at)=?",
            (today,),
        ).fetchone()
        skipped = conn.execute(
            """
            SELECT COUNT(*) FROM applications
            WHERE status='skipped'
              AND NOT (skip_reason='not_easy_apply' AND error_message='external apply')
              AND DATE(created_at)=?
            """,
            (today,),
        ).fetchone()
        result["applied"] = int(applied[0] or 0) if applied else 0
        result["skipped"] = int(skipped[0] or 0) if skipped else 0
    return result


def _get_apps_14days() -> dict:
    today = datetime.now().date()
    labels = [(today - timedelta(days=offset)).strftime("%m-%d") for offset in range(13, -1, -1)]
    counts = {label: 0 for label in labels}
    cutoff = (today - timedelta(days=13)).strftime("%Y-%m-%d")
    with sqlite3.connect(store.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*)
            FROM applications
            WHERE status='applied' AND DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
            """,
            (cutoff,),
        ).fetchall()
    for day, count in rows:
        try:
            label = datetime.fromisoformat(day).strftime("%m-%d")
            if label in counts:
                counts[label] = int(count or 0)
        except Exception:
            continue
    return {"labels": labels, "data": [counts[label] for label in labels]}


def _get_skip_reasons() -> dict:
    with sqlite3.connect(store.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(skip_reason, 'unknown') AS reason, COUNT(*)
            FROM applications
            WHERE status='skipped'
              AND NOT (skip_reason='not_easy_apply' AND error_message='external apply')
            GROUP BY COALESCE(skip_reason, 'unknown')
            ORDER BY COUNT(*) DESC, reason ASC
            LIMIT 7
            """
        ).fetchall()
    labels = [row[0] for row in rows]
    data = [int(row[1] or 0) for row in rows]
    return {"labels": labels, "data": data}


def _get_avg_fit_score():
    with sqlite3.connect(store.DB_PATH) as conn:
        row = conn.execute(
            "SELECT AVG(fit_score) FROM applications WHERE fit_score IS NOT NULL"
        ).fetchone()
    if not row or row[0] is None:
        return None
    try:
        return int(round(float(row[0])))
    except Exception:
        return None


def _get_notification_status(config: dict | None = None) -> list[dict] | None:
    config = config or {}
    notif_cfg = config.get("notifications", {}) or {}
    channels_cfg = notif_cfg.get("channels", {}) or {}
    if not notif_cfg.get("enabled") and not channels_cfg:
        return None

    stats_by_channel = {}
    if _HAS_NOTIFICATIONS:
        try:
            manager = NotificationManager.from_config(config, db_path=str(store.DB_PATH))
            stats = manager.get_stats(days=30)
            for row in stats.get("channels", []):
                stats_by_channel[row.get("channel")] = row
        except Exception:
            stats_by_channel = {}

    summaries = []
    icon_map = {
        "telegram": "send-fill",
        "email": "envelope-fill",
        "teams": "microsoft-teams",
        "discord": "discord",
        "webhook": "globe",
    }
    for name, cfg in channels_cfg.items():
        stat = stats_by_channel.get(name, {})
        summaries.append({
            "name": name.capitalize(),
            "type": name,
            "icon": icon_map.get(name, "bell"),
            "enabled": bool(cfg.get("enabled", False)),
            "last_sent_at": f"{stat.get('success', 0)}/{stat.get('total', 0)} success, avg {stat.get('avg_ms', 0)}ms",
        })
    return summaries or None


def _get_platforms() -> list[str]:
    with sqlite3.connect(store.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT platform
            FROM applications
            WHERE platform IS NOT NULL AND TRIM(platform) != ''
            ORDER BY platform
            """
        ).fetchall()
    return [str(row[0]) for row in rows if row and row[0]]


def _resolve_discovered_url(row: dict) -> str:
    url = (row.get("url") or "").strip()
    if url:
        return url
    platform = (row.get("platform") or "").lower()
    job_id = str(row.get("job_id") or "").strip()
    if platform == "linkedin" and job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    if platform == "indeed" and job_id:
        return f"https://www.indeed.com/viewjob?jk={job_id}"
    return ""


def _normalize_discovered_row(row: dict) -> dict:
    normalized = dict(row)
    title = (normalized.get("title") or "").strip()
    company = (normalized.get("company") or "").strip()
    job_id = str(normalized.get("job_id") or "").strip()
    platform = (normalized.get("platform") or "").strip().lower()
    synthetic_prefix = f"{platform.upper()} job " if platform else ""
    if synthetic_prefix and title.startswith(synthetic_prefix):
        title = ""
    if not title:
        if company and job_id:
            title = f"Untitled {platform or 'job'} @ {company}"
        elif job_id:
            title = f"Untitled {platform or 'job'}"
        elif company:
            title = f"Untitled job @ {company}"
        else:
            title = "Untitled job"
    normalized["title"] = title
    normalized["company"] = company or "Unknown company"
    normalized["location"] = (normalized.get("location") or "").strip() or "—"
    normalized["url"] = _resolve_discovered_url(normalized)
    normalized["platform"] = platform
    normalized["discovered_at_display"] = _format_local_unix(normalized.get("discovered_at"))
    return normalized


def _paginate(rows: list[dict], page: int = 1, page_size: int = 50):
    total = len(rows)
    total_pages = (total + page_size - 1) // page_size
    current_page = max(1, min(page, total_pages or 1))
    start = (current_page - 1) * page_size
    end = start + page_size
    if total_pages <= 7:
        page_range = list(range(1, total_pages + 1))
    else:
        page_range = [1]
        if current_page > 3:
            page_range.append("...")
        for pageno in range(max(2, current_page - 1), min(total_pages, current_page + 2)):
            page_range.append(pageno)
        if current_page < total_pages - 2:
            page_range.append("...")
        if total_pages > 1:
            page_range.append(total_pages)
    return rows[start:end], total_pages, current_page, page_range


def _applications_csv(rows: list[dict]) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "platform", "title", "company", "location", "status", "fit_score", "reason", "created_at", "url"])
    for row in rows:
        writer.writerow([
            row.get("id"),
            row.get("platform"),
            row.get("title"),
            row.get("company"),
            row.get("location"),
            row.get("status"),
            row.get("fit_score"),
            row.get("skip_reason") or row.get("error_message") or "",
            _format_local_datetime(row.get("created_at")),
            row.get("url"),
        ])
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


# ---------- PAGES ----------
@app.route("/")
def dashboard():
    cfg, config_error = _load_config_file()
    stats = store.get_stats()
    recent = store.list_applications(limit=10)
    runs = store.recent_runs(limit=5)
    latest_run = runs[0] if runs else None
    unanswered = load_unanswered()
    diag = controller.get_diagnostics()
    latest_screenshot = _latest_debug_screenshot()
    enabled_platforms = _load_platform_config_summary(cfg)
    rate_limit_statuses = _rate_limit_statuses(enabled_platforms)
    platform_states = _get_platform_states_for_dashboard(enabled_platforms)
    session_override = get_session_platforms()
    preferred_selection = get_preferred_platforms()
    return render_template(
        "dashboard.html",
        stats=stats, recent=recent, runs=runs, latest_run=latest_run,
        unanswered=unanswered, state=diag["state"], diag=diag,
        latest_screenshot=latest_screenshot,
        rate_limit_statuses=rate_limit_statuses,
        stats_today=_get_stats_today(),
        avg_fit_score=_get_avg_fit_score(),
        health_score=None,
        notifications=_get_notification_status(cfg),
        active_platform="LinkedIn Easy Apply",
        platform_states=platform_states,
        enabled_platforms=enabled_platforms,
        session_override=session_override,
        preferred_selection=preferred_selection,
        config_error=config_error,
    )


@app.route("/settings")
def settings():
    try:
        config = settings_load_config()
        env_display = get_env_for_display()
        warnings = validate_config(config)
        active_section = request.args.get("section", "search")
        profiles = []
        profile_history = []
        if active_section == "profiles":
            profiles = list_all_profiles()
            profile_history = get_profile_history()[-10:]
        return render_template(
            "settings.html",
            config=config,
            env_display=env_display,
            warnings=warnings,
            active_section=active_section,
            state=controller.get_state(),
            profiles=profiles,
            profile_history=profile_history,
        )
    except Exception as e:
        flash(f"Failed to load settings: {e}")
        return redirect(url_for("dashboard"))


@app.route("/settings/profiles")
def settings_profiles():
    return redirect(url_for("settings", section="profiles"))


@app.route("/settings/notifications")
def settings_notifications():
    return redirect(url_for("settings", section="credentials"))


@app.route("/settings/profiles/reset/<platform>", methods=["POST"])
def settings_profile_reset(platform):
    platform = (platform or "").strip().lower()
    if platform not in ("linkedin", "indeed", "glassdoor"):
        flash(f"Unknown platform: {platform}")
        return redirect(url_for("settings", section="profiles"))

    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag.get("is_zombie"):
        flash("Stop bot first before resetting profile.")
        return redirect(url_for("settings", section="profiles"))

    launch = (request.form.get("launch_chrome", "true") or "true").lower() == "true"
    result = reset_profile(platform, launch_chrome=launch)
    if result.get("success"):
        flash(f"{platform.title()} profile reset. {result.get('message', '')}")
    else:
        flash(f"Reset failed: {result.get('message', 'unknown error')}")
    return redirect(url_for("settings", section="profiles"))


@app.route("/settings/profiles/cleanup", methods=["POST"])
def settings_profile_cleanup():
    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag.get("is_zombie"):
        flash("Stop bot first before cleaning profile backups.")
        return redirect(url_for("settings", section="profiles"))

    try:
        keep_count = max(1, min(10, int(request.form.get("keep_count", "3"))))
    except Exception:
        keep_count = 3
    deleted = cleanup_old_backups(keep_count=keep_count)
    flash(f"Cleaned up {deleted} old backup(s). Kept newest {keep_count}.")
    return redirect(url_for("settings", section="profiles"))


@app.route("/settings/save/<section>", methods=["POST"])
def settings_save(section):
    try:
        form_data = request.form.to_dict(flat=False)
        if section == "search":
            config = settings_load_config()
            filters_cfg = config.setdefault("filters", {})
            filters_cfg.update({
                "title_keywords_include": _parse_list(form_data.get("title_include", [""])[0]),
                "title_keywords_exclude": _parse_list(form_data.get("title_exclude", [""])[0]),
                "description_keywords_exclude": _parse_list(form_data.get("description_exclude", [""])[0]),
                "company_blacklist": _parse_list(form_data.get("company_blacklist", [""])[0]),
                "min_salary": int(form_data.get("min_salary", ["0"])[0] or 0),
                "skip_already_applied": "skip_already_applied" in form_data,
            })
            queries = _parse_list(form_data.get("queries", [""])[0])
            location = form_data.get("location", [""])[0]
            max_apply = int(form_data.get("max_apply_per_run", ["0"])[0] or 0)
            for platform_name in config.get("platforms", {}):
                search_cfg = config["platforms"][platform_name].setdefault("search", {})
                if queries:
                    search_cfg["queries"] = queries
                if location:
                    search_cfg["location"] = location
                if max_apply > 0:
                    config["platforms"][platform_name]["max_apply_per_run"] = max_apply
            success, msg = settings_save_config(config)
        elif section == "personal":
            new_values = {key: values[0] for key, values in form_data.items()}
            success, msg = update_config_section("personal", new_values)
        elif section == "behavior":
            config = settings_load_config()
            config.setdefault("stealth", {}).update({
                "min_delay_sec": float(form_data.get("min_delay_sec", ["2"])[0] or 2),
                "max_delay_sec": float(form_data.get("max_delay_sec", ["4.5"])[0] or 4.5),
                "pause_every_n_applications": int(form_data.get("pause_every_n", ["5"])[0] or 5),
                "pause_seconds": int(form_data.get("pause_seconds", ["60"])[0] or 60),
            })
            config.setdefault("ai", {}).update({
                "enabled": "ai_enabled" in form_data,
                "model": form_data.get("ai_model", [""])[0],
                "resume_tailoring": "resume_tailoring" in form_data,
                "cover_letter": "cover_letter" in form_data,
                "fit_scoring": "fit_scoring" in form_data,
            })
            env = load_env()
            env["HEADLESS"] = "true" if "headless" in form_data else "false"
            save_env(env)
            success, msg = settings_save_config(config)
        elif section == "credentials":
            env = load_env()
            normal_keys = [
                "LINKEDIN_EMAIL", "INDEED_EMAIL", "AI_API_KEY", "AI_BASE_URL",
                "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "CAPTCHA_API_KEY",
                "FLASK_SECRET_KEY", "WEB_HOST", "WEB_PORT", "LOG_LEVEL",
            ]
            for key in normal_keys:
                form_key = key.lower()
                if form_key in form_data:
                    value = form_data[form_key][0]
                    if value and not value.startswith("****"):
                        env[key] = value
            secret_keys = ["LINKEDIN_PASSWORD", "INDEED_PASSWORD", "LINKEDIN_TOTP_SECRET"]
            for key in secret_keys:
                form_key = key.lower()
                if form_key in form_data and form_data[form_key][0]:
                    env[key] = form_data[form_key][0]
            success, msg = save_env(env)
        else:
            flash(f"Unknown section: {section}")
            return redirect(url_for("settings"))

        flash((f"Saved {section}: {msg}") if success else (f"Save failed: {msg}"))
        return redirect(url_for("settings", section=section))
    except Exception as e:
        flash(f"Save error: {e}")
        return redirect(url_for("settings", section=section))


@app.route("/applications")
def applications():
    status = request.args.get("status") or None
    platform = request.args.get("platform") or None
    page = max(1, request.args.get("page", default=1, type=int))
    all_rows = store.list_applications(status=status, limit=2000)
    if platform:
        all_rows = [row for row in all_rows if (row.get("platform") or "").lower() == platform.lower()]
    if request.args.get("export") == "csv":
        return _applications_csv(all_rows)
    rows, total_pages, current_page, page_range = _paginate(all_rows, page=page, page_size=50)
    return render_template(
        "applications.html",
        rows=rows,
        current=status,
        platforms=_get_platforms(),
        total_pages=total_pages,
        current_page=current_page,
        page_range=page_range,
        page_size=50,
        total_rows=len(all_rows),
        show_ghost_status=False,
    )


@app.route("/application/<int:app_id>")
def application_detail(app_id):
    row = store.get_application(app_id)
    if not row:
        flash("Application not found")
        return redirect(url_for("applications"))
    return render_template("application_detail.html", row=row, show_interview_prep=False)


@app.route("/discovered")
def discovered():
    status = request.args.get("status") or None
    platform = request.args.get("platform") or None
    min_fit_raw = request.args.get("min_fit", "").strip()
    days_raw = request.args.get("days", "").strip()
    min_fit = int(min_fit_raw) if min_fit_raw.isdigit() else None
    days = int(days_raw) if days_raw.isdigit() else None

    jobs = discovered_store.list_discovered(
        status=status,
        platform=platform,
        min_fit=min_fit,
        days=days,
        limit=500,
    )
    jobs = [_normalize_discovered_row(job) for job in jobs]
    stats = discovered_store.get_stats()
    discovery_session = get_discovery_session()
    if discovery_session:
        discovery_session = dict(discovery_session)
        discovery_session["started_at_display"] = _format_local_unix(
            discovery_session.get("started_at")
        )
    return render_template(
        "discovered.html",
        jobs=jobs,
        stats=stats,
        total=stats.get("total", 0),
        current_status=status,
        discovery_session=discovery_session,
    )


@app.route("/discovered/trigger", methods=["POST"])
def discovered_trigger():
    global _runner_thread
    _, config_error = _load_config_file()
    if config_error:
        flash(f"Config error in config.yaml: {config_error}")
        return redirect(url_for("discovered"))

    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag.get("is_zombie"):
        flash("Bot already running. Wait for it to finish.")
        return redirect(url_for("discovered"))

    platforms_raw = (request.form.get("platforms") or "").strip()
    platforms = [p.strip() for p in platforms_raw.split(",") if p.strip()]
    platforms = list(dict.fromkeys(platforms))
    if not platforms:
        flash("No platforms selected for discovery.")
        return redirect(url_for("discovered"))

    # Discovery must always start in scrape/curation mode, not resume a stale apply queue.
    queue_path = Path("data/.control/apply_queue.json")
    try:
        queue_path.unlink(missing_ok=True)
    except Exception:
        pass

    try:
        max_per_session = max(1, min(500, int(request.form.get("max_per_session", "100"))))
    except Exception:
        max_per_session = 100
    try:
        scroll_depth = max(1, min(100, int(request.form.get("scroll_depth", "15"))))
    except Exception:
        scroll_depth = 15

    if not set_discovery_session(platforms, max_per_session, scroll_depth):
        flash("Could not start discovery session.")
        return redirect(url_for("discovered"))

    set_session_platforms(platforms, mode="sequential")

    controller.reset()
    controller.set_state("running")
    controller.beat()
    tracker = get_tracker()
    tracker.reset(keep_logs=False)
    tracker.set_state("running")
    tracker.add_activity("Discovery scan requested", "info")
    _runner_thread = threading.Thread(target=run_bot, daemon=True)
    _runner_thread.start()
    flash(
        f"Discovery started: {', '.join(platforms)} "
        f"(cap: {max_per_session} jobs, scroll: {scroll_depth})."
    )
    return redirect(url_for("dashboard"))


@app.route("/discovered/status")
def discovered_status():
    session = get_discovery_session()
    if session:
        session = dict(session)
        session["started_at_display"] = _format_local_unix(session.get("started_at"))
    return jsonify({
        "session": session,
        "stats": discovered_store.get_stats(),
        "bot_state": controller.get_state(),
    })


@app.route("/discovered/action/<int:job_id>", methods=["POST"])
def discovered_action(job_id):
    action = (request.form.get("action") or "").strip()
    allowed = {
        discovered_store.STATUS_DISCOVERED,
        discovered_store.STATUS_SELECTED,
        discovered_store.STATUS_AUTO_APPLY,
        discovered_store.STATUS_SKIPPED,
        discovered_store.STATUS_SAVED,
        discovered_store.STATUS_APPLIED,
        discovered_store.STATUS_FAILED,
    }
    if action not in allowed:
        flash("Invalid discovery action.")
        return redirect(url_for("discovered"))
    updated = discovered_store.update_status([job_id], action)
    flash(f"Updated {updated} job(s) to {action}." if updated else "Nothing was updated.")
    return redirect(url_for("discovered"))


@app.route("/discovered/bulk-action", methods=["POST"])
def discovered_bulk_action():
    action = (request.form.get("action") or "").strip()
    ids_raw = request.form.get("job_ids") or ""
    job_ids = [int(value) for value in ids_raw.split(",") if value.strip().isdigit()]
    if not job_ids:
        flash("No discovered jobs selected.")
        return redirect(url_for("discovered"))
    allowed = {
        discovered_store.STATUS_DISCOVERED,
        discovered_store.STATUS_SELECTED,
        discovered_store.STATUS_AUTO_APPLY,
        discovered_store.STATUS_SKIPPED,
        discovered_store.STATUS_SAVED,
    }
    if action not in allowed:
        flash("Invalid bulk action.")
        return redirect(url_for("discovered"))
    updated = discovered_store.update_status(job_ids, action)
    flash(f"Updated {updated} discovered job(s) to {action}.")
    return redirect(url_for("discovered"))


@app.route("/discovered/apply-selected", methods=["POST"])
def discovered_apply_selected():
    global _runner_thread
    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag["is_zombie"]:
        flash("Bot already running.")
        return redirect(url_for("discovered"))

    selected_jobs = discovered_store.list_discovered(
        status=discovered_store.STATUS_SELECTED,
        limit=200,
    )
    if not selected_jobs:
        flash("No jobs marked for apply.")
        return redirect(url_for("discovered"))

    queue = [_normalize_discovered_row(job) for job in selected_jobs]
    queue_payload = [
        {
            "discovered_id": job["id"],
            "platform": job["platform"],
            "job_id": job["job_id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "url": job["url"],
            "fit_score": job.get("fit_score"),
            "fit_reasoning": job.get("fit_reasoning"),
        }
        for job in queue
    ]

    queue_path = Path("data/.control/apply_queue.json")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(queue_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    discovered_store.update_status(
        [job["id"] for job in queue],
        discovered_store.STATUS_AUTO_APPLY,
    )

    platforms = sorted({job["platform"] for job in queue if job.get("platform")})
    if platforms:
        set_session_platforms(platforms, "sequential")
    else:
        clear_session_override()

    controller.reset()
    controller.set_state("running")
    controller.beat()
    tracker = get_tracker()
    tracker.reset(keep_logs=False)
    tracker.set_state("running")
    tracker.add_activity("Discovered apply queue started", "info")
    _runner_thread = threading.Thread(target=run_bot, daemon=True)
    _runner_thread.start()
    flash(f"Started apply queue for {len(queue_payload)} discovered job(s).")
    return redirect(url_for("discovered"))


@app.route("/discovered/schedule", methods=["POST"])
def discovered_schedule():
    ids_raw = request.form.get("job_ids") or ""
    schedule_time = (request.form.get("schedule_time") or "").strip()
    job_ids = [int(value) for value in ids_raw.split(",") if value.strip().isdigit()]
    if not job_ids:
        flash("No discovered jobs selected.")
        return redirect(url_for("discovered"))
    if not schedule_time:
        flash("Schedule time is required.")
        return redirect(url_for("discovered"))
    try:
        dt = datetime.fromisoformat(schedule_time)
        scheduled_at = int(dt.timestamp())
    except Exception:
        flash("Invalid schedule time.")
        return redirect(url_for("discovered"))
    updated = discovered_store.update_status(
        job_ids,
        discovered_store.STATUS_AUTO_APPLY,
        scheduled_at=scheduled_at,
    )
    flash(f"Scheduled {updated} discovered job(s).")
    return redirect(url_for("discovered"))


@app.route("/questions", methods=["GET", "POST"])
def questions():
    if request.method == "POST":
        q = (request.form.get("question") or "").strip()
        a = (request.form.get("answer") or "").strip()
        if q and a:
            resolve_unanswered(q, a)
            flash(f"Saved: {q}")
        return redirect(url_for("questions"))
    return render_template(
        "questions.html",
        answers=load_answers(),
        unanswered=load_unanswered(),
    )


@app.route("/questions/delete", methods=["POST"])
def delete_question():
    q = request.form.get("question")
    answers = load_answers()
    if q in answers:
        del answers[q]
        save_answers(answers)
        flash("Removed.")
    return redirect(url_for("questions"))


@app.route("/questions/clear-unanswered", methods=["POST"])
def clear_unanswered_route():
    clear_unanswered()
    flash("Unanswered queue cleared.")
    return redirect(url_for("questions"))


# ---------- CONTROL ----------
@app.route("/control/start", methods=["POST"])
def control_start():
    global _runner_thread
    _, config_error = _load_config_file()
    if config_error:
        flash(f"Config error in config.yaml: {config_error}")
        return redirect(url_for("dashboard"))
    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag["is_zombie"]:
        flash("Bot already running.")
        return redirect(url_for("dashboard"))

    preferred = get_preferred_platforms() or {}
    platforms = preferred.get("platforms") or []
    mode = (preferred.get("mode") or "sequential").strip() or "sequential"
    if platforms:
        set_session_platforms(platforms, mode)
        flash_msg = f"Bot started: {', '.join(platforms)} ({mode})."
    else:
        clear_session_override()
        flash_msg = "Bot started in background."
    controller.reset()
    controller.set_state("running")
    controller.beat()
    tracker = get_tracker()
    tracker.reset(keep_logs=False)
    tracker.set_state("running")
    tracker.add_activity("Start requested from dashboard", "info")
    _runner_thread = threading.Thread(target=run_bot, daemon=True)
    _runner_thread.start()
    flash(flash_msg)
    return redirect(url_for("dashboard"))


@app.route("/control/start_platform", methods=["POST"])
def control_start_platform():
    global _runner_thread
    cfg, config_error = _load_config_file()
    if config_error:
        flash(f"Config error in config.yaml: {config_error}")
        return redirect(url_for("dashboard"))
    diag = controller.get_diagnostics()
    if diag["state"] in ("running", "paused") and not diag["is_zombie"]:
        flash("Bot already running.")
        return redirect(url_for("dashboard"))

    platforms_raw = (request.form.get("platforms") or "").strip()
    if not platforms_raw:
        platforms_raw = ",".join(request.form.getlist("platforms_checks"))
    mode = (request.form.get("mode") or "sequential").strip() or "sequential"

    if platforms_raw == "all":
        clear_session_override()
        clear_preferred_platforms()
        flash_msg = "Bot started (all enabled platforms)."
    else:
        platforms_list = [p.strip() for p in platforms_raw.split(",") if p.strip()]
        platforms_list = list(dict.fromkeys(platforms_list))
        if not platforms_list:
            flash("No platforms selected.")
            return redirect(url_for("dashboard"))
        set_session_platforms(platforms_list, mode)
        set_preferred_platforms(platforms_list, mode)
        flash_msg = f"Bot started: {', '.join(platforms_list)} ({mode})."

    controller.reset()
    controller.set_state("running")
    controller.beat()
    tracker = get_tracker()
    tracker.reset(keep_logs=False)
    tracker.set_state("running")
    tracker.add_activity("Platform start requested from dashboard", "info")
    _runner_thread = threading.Thread(target=run_bot, daemon=True)
    _runner_thread.start()
    flash(flash_msg)
    return redirect(url_for("dashboard"))


@app.route("/control/pause", methods=["POST"])
def control_pause():
    controller.set_command("pause")
    get_tracker().set_state("paused")
    get_tracker().add_activity("Pause requested", "warning")
    flash("Pause requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/resume", methods=["POST"])
def control_resume():
    controller.set_command("resume")
    get_tracker().set_state("running")
    get_tracker().add_activity("Resume requested", "info")
    flash("Resume requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/stop", methods=["POST"])
def control_stop():
    controller.set_command("stop")
    get_tracker().set_state("stopped")
    get_tracker().add_activity("Stop requested", "warning")
    flash("Stop requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/reset", methods=["POST"])
def control_reset():
    """PATCH 5: Force-reset stuck state files."""
    diag_before = controller.get_diagnostics()
    controller.reset()
    get_tracker().reset(keep_logs=False)
    flash(f"🧹 State reset. Was: {diag_before['state']}, zombie={diag_before['is_zombie']}")
    return redirect(url_for("dashboard"))


@app.route("/control/ai-test", methods=["POST"])
def control_ai_test():
    """PATCH 5: Test AI connection on demand."""
    try:
        cfg, config_error = _load_config_file()
        if config_error:
            flash(f"Config error in config.yaml: {config_error}")
            return redirect(url_for("dashboard"))
        ai_cfg = cfg.get("ai", {}) or {}
        if not ai_cfg.get("enabled"):
            flash("AI is disabled in config.yaml")
            return redirect(url_for("dashboard"))
        ai_cfg = dict(ai_cfg)
        ai_cfg["timeout_seconds"] = min(int(ai_cfg.get("timeout_seconds", 60)), 12)
        ai_cfg["max_retries"] = 0
        from packages.ai.provider import AIProvider
        ai = AIProvider(ai_cfg)
        ok, msg = ai.test_connection()
        if ok:
            flash(f"✅ AI works: {msg}")
        else:
            flash(f"❌ AI failed: {msg}")
    except Exception as e:
        flash(f"❌ AI test error: {e}")
    return redirect(url_for("dashboard"))


@app.route("/control/notif-test", methods=["POST"])
def control_notif_test():
    if not _HAS_NOTIFICATIONS or NotificationManager is None:
        flash("Notifications module is not available.")
        return redirect(url_for("dashboard"))
    try:
        cfg, config_error = _load_config_file()
        if config_error:
            flash(f"Config error in config.yaml: {config_error}")
            return redirect(url_for("dashboard"))
        manager = NotificationManager.from_config(cfg, db_path=str(store.DB_PATH))
        results = manager.test_all()
        if not results:
            flash("No active notification channels configured.")
            return redirect(url_for("dashboard"))
        parts = []
        for channel, result in results.items():
            if isinstance(result, tuple):
                ok, msg = result
            else:
                ok = bool(result)
                msg = "OK" if ok else "Failed"
            parts.append(f"{channel}: {'OK' if ok else 'FAIL'} ({msg})")
        flash("Notification test: " + " | ".join(parts))
    except Exception as e:
        flash(f"Notification test failed: {e}")
    return redirect(url_for("dashboard"))


@app.route("/control/rate_limit/reset", methods=["POST"])
def control_rate_limit_reset():
    platform = (request.form.get("platform") or "linkedin").strip() or "linkedin"
    try:
        limiter = SmartRateLimiter(store.DB_PATH, platform, _load_global_limits_config())
        limiter.reset()
        flash(f"Rate limiter reset for {platform}.")
    except Exception as e:
        flash(f"Rate limiter reset failed: {e}")
    return redirect(url_for("dashboard"))


# ---------- API ----------
@app.route("/api/state")
def api_state():
    return jsonify({
        "state": controller.get_state(),
        "stats": store.get_stats(),
        "diag": controller.get_diagnostics(),
    })


@app.route("/api/dashboard")
def api_dashboard():
    unanswered = load_unanswered()
    recent = store.list_applications(limit=10)
    runs = store.recent_runs(limit=1)
    latest_run = runs[0] if runs else None
    cfg, config_error = _load_config_file()
    enabled_platforms = _load_platform_config_summary(cfg)
    rate_limit_statuses = _rate_limit_statuses(enabled_platforms)
    for row in recent:
        row["created_at_display"] = _format_local_datetime(row.get("created_at"))
    if latest_run:
        latest_run["started_at_display"] = _format_local_datetime(latest_run.get("started_at"))
        latest_run["finished_at_display"] = _format_local_datetime(latest_run.get("finished_at"))
    return jsonify({
        "state": controller.get_state(),
        "stats": store.get_stats(),
        "diag": controller.get_diagnostics(),
        "recent": recent,
        "latest_run": latest_run,
        "latest_screenshot": _latest_debug_screenshot(),
        "unanswered_count": len(unanswered),
        "rate_limit_status": rate_limit_statuses[0] if rate_limit_statuses else None,
        "rate_limit_statuses": rate_limit_statuses,
        "stats_today": _get_stats_today(),
        "avg_fit_score": _get_avg_fit_score(),
        "apps_14days": _get_apps_14days(),
        "skip_reasons": _get_skip_reasons(),
        "platform_states": _get_platform_states_for_dashboard(enabled_platforms),
        "preferred_selection": get_preferred_platforms(),
        "config_error": config_error,
    })


@app.route("/api/rate_limit/<platform>")
def api_rate_limit(platform):
    return jsonify(_rate_limit_status(platform) or {"platform": platform})


@app.route("/api/realtime/progress")
def api_realtime_progress():
    try:
        snapshot = get_tracker().get_snapshot()
        return jsonify(snapshot)
    except Exception as e:
        return jsonify({"error": str(e), "state": "idle"}), 500


@app.route("/api/platform_states")
def api_platform_states():
    return jsonify(_get_platform_states_for_dashboard())


@app.route("/api/logs/tail")
def api_logs_tail():
    log_file = Path("data/logs/bot.log")
    if not log_file.exists():
        return Response("(no logs yet)", mimetype="text/plain")
    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-100:]
    return Response("\n".join(lines), mimetype="text/plain")


if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "5050"))
    app.run(host=host, port=port, debug=False)
