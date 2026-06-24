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
from packages.storage.answers import (
    load_answers, save_answers, load_unanswered, clear_unanswered,
    resolve_unanswered,
)
from packages.extractors.rate_limiter import get_status_for_dashboard, SmartRateLimiter
from apps.worker.control import controller
from apps.worker.runner import run_bot

load_dotenv()
store.init_db()

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


app.jinja_env.filters["localdt"] = _format_local_datetime


@app.context_processor
def _inject_layout_state():
    unanswered = load_unanswered()
    return {
        "state": controller.get_state(),
        "stats": store.get_stats(),
        "unanswered_count": len(unanswered),
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


def _load_global_limits_config() -> dict:
    try:
        import yaml
        cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8")) or {}
        return cfg.get("global_limits", {}) or {}
    except Exception:
        return {}


def _rate_limit_status(platform: str = "linkedin"):
    try:
        return get_status_for_dashboard(store.DB_PATH, platform, _load_global_limits_config())
    except Exception:
        return None


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
    stats = store.get_stats()
    recent = store.list_applications(limit=10)
    runs = store.recent_runs(limit=5)
    latest_run = runs[0] if runs else None
    unanswered = load_unanswered()
    diag = controller.get_diagnostics()
    latest_screenshot = _latest_debug_screenshot()
    rate_limit_status = _rate_limit_status()
    return render_template(
        "dashboard.html",
        stats=stats, recent=recent, runs=runs, latest_run=latest_run,
        unanswered=unanswered, state=diag["state"], diag=diag,
        latest_screenshot=latest_screenshot,
        rate_limit_status=rate_limit_status,
        stats_today=_get_stats_today(),
        avg_fit_score=_get_avg_fit_score(),
        health_score=None,
        notifications=None,
        active_platform="LinkedIn Easy Apply",
    )


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
    diag = controller.get_diagnostics()
    if diag["state"] == "running" and not diag["is_zombie"]:
        flash("Bot already running.")
        return redirect(url_for("dashboard"))

    # Reset state for clean start
    controller.reset()
    _runner_thread = threading.Thread(target=run_bot, daemon=True)
    _runner_thread.start()
    flash("Bot started in background.")
    return redirect(url_for("dashboard"))


@app.route("/control/pause", methods=["POST"])
def control_pause():
    controller.set_command("pause")
    flash("Pause requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/resume", methods=["POST"])
def control_resume():
    controller.set_command("resume")
    flash("Resume requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/stop", methods=["POST"])
def control_stop():
    controller.set_command("stop")
    flash("Stop requested.")
    return redirect(url_for("dashboard"))


@app.route("/control/reset", methods=["POST"])
def control_reset():
    """PATCH 5: Force-reset stuck state files."""
    diag_before = controller.get_diagnostics()
    controller.reset()
    flash(f"🧹 State reset. Was: {diag_before['state']}, zombie={diag_before['is_zombie']}")
    return redirect(url_for("dashboard"))


@app.route("/control/ai-test", methods=["POST"])
def control_ai_test():
    """PATCH 5: Test AI connection on demand."""
    import yaml
    try:
        cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
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
        "rate_limit_status": _rate_limit_status(),
        "stats_today": _get_stats_today(),
        "avg_fit_score": _get_avg_fit_score(),
        "apps_14days": _get_apps_14days(),
        "skip_reasons": _get_skip_reasons(),
    })


@app.route("/api/rate_limit/<platform>")
def api_rate_limit(platform):
    return jsonify(_rate_limit_status(platform) or {"platform": platform})


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
