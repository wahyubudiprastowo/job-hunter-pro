"""
Thread-safe in-memory realtime tracker for the dashboard.

This stays additive to the existing DB-backed dashboard:
- DB remains source of truth for historical totals
- tracker is only for live "what is the bot doing now?" state
"""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional


class RealtimeTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset(keep_logs=False)

    def reset(self, keep_logs: bool = True):
        with self._lock:
            self._state = "idle"
            self._started_at: Optional[float] = None
            self._current_job = None
            self._current_step = "idle"
            self._step_progress = 0
            self._run_progress = 0
            self._run_target = 0
            self._run_applied = 0
            self._run_skipped = 0
            self._run_failed = 0
            self._run_needs = 0
            if not keep_logs or not hasattr(self, "_recent_logs"):
                self._recent_logs = deque(maxlen=40)
            if not keep_logs or not hasattr(self, "_activities"):
                self._activities = deque(maxlen=12)

    def set_state(self, state: str):
        with self._lock:
            self._state = state or "idle"
            if self._state == "running" and self._started_at is None:
                self._started_at = time.time()
            elif self._state in ("idle", "stopped", "error"):
                self._started_at = None
                self._current_job = None
                self._current_step = "idle"
                self._step_progress = 0

    def set_current_job(
        self,
        title: str = "",
        company: str = "",
        platform: str = "",
        step: str = "Loading",
        fit_score: Optional[int] = None,
    ):
        with self._lock:
            self._current_job = {
                "title": title or "",
                "company": company or "",
                "platform": platform or "",
                "step": step or "Loading",
                "fit_score": fit_score,
                "started_at": int(time.time()),
            }
            self._current_step = step or "Loading"

    def set_step(self, step: str, progress: int = 0):
        with self._lock:
            self._current_step = step or "idle"
            self._step_progress = min(100, max(0, int(progress or 0)))
            if self._current_job:
                self._current_job["step"] = self._current_step

    def set_run_progress(self, applied: int, target: int):
        with self._lock:
            self._run_applied = int(applied or 0)
            self._run_target = int(target or 0)
            if self._run_target > 0:
                self._run_progress = round((self._run_applied / self._run_target) * 100)
            else:
                self._run_progress = 0

    def set_run_counters(self, applied: int, skipped: int, failed: int, needs: int):
        with self._lock:
            self._run_applied = int(applied or 0)
            self._run_skipped = int(skipped or 0)
            self._run_failed = int(failed or 0)
            self._run_needs = int(needs or 0)

    def add_log(self, line: str):
        text = (line or "").strip()
        if not text:
            return
        with self._lock:
            self._recent_logs.append({"ts": int(time.time()), "text": text})

    def add_activity(self, text: str, level: str = "info"):
        if not text:
            return
        with self._lock:
            self._activities.appendleft(
                {
                    "ts": int(time.time()),
                    "text": text,
                    "level": level or "info",
                    "display_time": datetime.now().strftime("%H:%M:%S"),
                }
            )

    def get_snapshot(self) -> dict:
        with self._lock:
            elapsed = int(time.time() - self._started_at) if self._started_at else 0
            eta_min = 0
            if self._run_progress > 0 and self._started_at:
                total_estimated_sec = elapsed / max(self._run_progress / 100, 0.01)
                eta_min = max(0, round((total_estimated_sec - elapsed) / 60))

            return {
                "state": self._state,
                "elapsed_sec": elapsed,
                "elapsed_label": _format_elapsed(elapsed),
                "current_job": self._current_job,
                "current_step": self._current_step,
                "step_progress": self._step_progress,
                "run_progress": self._run_progress,
                "run_applied": self._run_applied,
                "run_target": self._run_target,
                "run_skipped": self._run_skipped,
                "run_failed": self._run_failed,
                "run_needs": self._run_needs,
                "run_subtitle": f"{self._run_applied} / {self._run_target}" if self._run_target else "0 / 0",
                "eta_min": eta_min,
                "recent_logs": [item["text"] for item in list(self._recent_logs)[-20:]],
                "activities": list(self._activities)[:8],
            }


def _format_elapsed(seconds: int) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


_tracker = RealtimeTracker()


def get_tracker() -> RealtimeTracker:
    return _tracker
