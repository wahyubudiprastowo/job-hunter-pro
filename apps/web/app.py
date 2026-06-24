"""Flask dashboard — PATCH 5: + Reset button + AI test + diagnostics."""
import os
import json
import threading
from datetime import datetime, timezone
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
    return render_template(
        "dashboard.html",
        stats=stats, recent=recent, runs=runs, latest_run=latest_run,
        unanswered=unanswered, state=diag["state"], diag=diag,
        latest_screenshot=latest_screenshot,
    )


@app.route("/applications")
def applications():
    status = request.args.get("status") or None
    rows = store.list_applications(status=status, limit=300)
    return render_template("applications.html", rows=rows, current=status)


@app.route("/application/<int:app_id>")
def application_detail(app_id):
    row = store.get_application(app_id)
    if not row:
        flash("Application not found")
        return redirect(url_for("applications"))
    return render_template("application_detail.html", row=row)


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
    })


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
