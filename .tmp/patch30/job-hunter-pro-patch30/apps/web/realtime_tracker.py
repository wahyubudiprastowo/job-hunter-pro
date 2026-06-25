"""
Real-time Progress Tracker (Patch 30).

Provides /api/realtime/progress endpoint for frontend live updates.
Tracks current job, step, percentage, KPIs in memory.
"""
from __future__ import annotations
import time
import threading
from typing import Optional
from pathlib import Path
from collections import deque


class RealtimeTracker:
    """Thread-safe in-memory progress tracker."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._current_job = None
        self._current_step = "idle"
        self._step_progress = 0  # 0-100
        self._run_progress = 0
        self._run_target = 0
        self._run_applied = 0
        self._kpis = {
            "applied": 0,
            "skipped": 0,
            "needs": 0,
            "failed": 0,
            "external": 0,
            "applied_today": 0,
            "fit_score_avg": 0,
        }
        self._recent_logs = deque(maxlen=30)
        self._activities = deque(maxlen=10)
        self._state = "idle"
        self._started_at = None
    
    def set_state(self, state: str):
        with self._lock:
            self._state = state
            if state == "running" and self._started_at is None:
                self._started_at = time.time()
            elif state in ("idle", "stopped"):
                self._started_at = None
                self._current_job = None
                self._current_step = "idle"
    
    def set_current_job(self, title: str = "", company: str = "", platform: str = "", 
                        step: str = "Loading", fit_score: Optional[int] = None):
        with self._lock:
            self._current_job = {
                "title": title,
                "company": company,
                "platform": platform,
                "step": step,
                "fit_score": fit_score,
                "started_at": int(time.time()),
            }
            self._current_step = step
    
    def set_step(self, step: str, progress: int = 0):
        with self._lock:
            self._current_step = step
            self._step_progress = min(100, max(0, progress))
            if self._current_job:
                self._current_job["step"] = step
    
    def set_run_progress(self, applied: int, target: int):
        with self._lock:
            self._run_applied = applied
            self._run_target = target
            self._run_progress = round((applied / target) * 100) if target > 0 else 0
    
    def update_kpi(self, key: str, value):
        with self._lock:
            self._kpis[key] = value
    
    def increment_kpi(self, key: str, by: int = 1):
        with self._lock:
            self._kpis[key] = self._kpis.get(key, 0) + by
    
    def add_log(self, line: str):
        with self._lock:
            self._recent_logs.append({
                "ts": int(time.time()),
                "text": line,
            })
    
    def add_activity(self, text: str, level: str = "info"):
        with self._lock:
            self._activities.append({
                "ts": int(time.time()),
                "text": text,
                "level": level,
            })
    
    def get_snapshot(self) -> dict:
        with self._lock:
            elapsed = int(time.time() - self._started_at) if self._started_at else 0
            
            # Estimate ETA
            eta_min = 0
            if self._run_progress > 0 and self._started_at:
                total_estimated_sec = elapsed / (self._run_progress / 100)
                remaining_sec = total_estimated_sec - elapsed
                eta_min = max(0, round(remaining_sec / 60))
            
            return {
                "state": self._state,
                "elapsed_sec": elapsed,
                "current_job": self._current_job,
                "current_step": self._current_step,
                "step_progress": self._step_progress,
                "run_progress": self._run_progress,
                "run_applied": self._run_applied,
                "run_target": self._run_target,
                "run_subtitle": f"{self._run_applied} / {self._run_target}",
                "eta_min": eta_min,
                "progress": {
                    "kpis": dict(self._kpis),
                    "bars": {
                        "step": self._step_progress,
                        "run": self._run_progress,
                    },
                    "run_progress": self._run_progress,
                    "run_subtitle": f"{self._run_applied} / {self._run_target}",
                },
                "recent_logs": [item["text"] for item in list(self._recent_logs)[-15:]],
                "activities": list(self._activities),
            }


# Singleton
_tracker = RealtimeTracker()


def get_tracker() -> RealtimeTracker:
    return _tracker
