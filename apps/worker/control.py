"""
Lightweight controller for pause/resume/stop.

PATCH 5: heartbeat-based zombie detection.
If state="running" but heartbeat is stale (>30s), it's a zombie → treat as idle.
"""
import time
import os
from pathlib import Path
from loguru import logger

CTRL_DIR = Path("data/.control")
CTRL_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = CTRL_DIR / "state.txt"
COMMAND_FILE = CTRL_DIR / "command.txt"
HEARTBEAT_FILE = CTRL_DIR / "heartbeat.txt"
PID_FILE = CTRL_DIR / "pid.txt"

HEARTBEAT_TIMEOUT = 30  # seconds


class Controller:
    def get_state(self) -> str:
        """Return effective state, auto-recover from zombie."""
        if not STATE_FILE.exists():
            return "idle"
        state = STATE_FILE.read_text(encoding="utf-8").strip() or "idle"
        # Zombie detection: state says "running" but heartbeat stale
        if state == "running":
            if self._is_zombie():
                logger.warning("⚠️  Zombie state detected — auto-resetting to idle.")
                self.reset()
                return "idle"
        return state

    def _is_zombie(self) -> bool:
        """Is the running state actually a zombie?"""
        if not HEARTBEAT_FILE.exists():
            return True
        try:
            last = float(HEARTBEAT_FILE.read_text(encoding="utf-8").strip())
            age = time.time() - last
            return age > HEARTBEAT_TIMEOUT
        except (ValueError, OSError):
            return True

    def set_state(self, state: str):
        STATE_FILE.write_text(state, encoding="utf-8")

    def get_command(self) -> str:
        if COMMAND_FILE.exists():
            return COMMAND_FILE.read_text(encoding="utf-8").strip()
        return ""

    def set_command(self, cmd: str):
        COMMAND_FILE.write_text(cmd, encoding="utf-8")

    def clear_command(self):
        if COMMAND_FILE.exists():
            try:
                COMMAND_FILE.unlink()
            except OSError:
                pass

    def beat(self):
        """Update heartbeat — call regularly from runner."""
        HEARTBEAT_FILE.write_text(str(time.time()), encoding="utf-8")
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def reset(self):
        """Force-reset all state files (manual recovery)."""
        for f in (STATE_FILE, COMMAND_FILE, HEARTBEAT_FILE, PID_FILE):
            try:
                if f.exists():
                    f.unlink()
            except OSError:
                pass

    def get_diagnostics(self) -> dict:
        """Return state info for dashboard."""
        info = {
            "state": "idle",
            "command": None,
            "heartbeat_age_sec": None,
            "pid": None,
            "is_zombie": False,
        }
        if STATE_FILE.exists():
            info["state"] = STATE_FILE.read_text(encoding="utf-8").strip() or "idle"
        if COMMAND_FILE.exists():
            info["command"] = COMMAND_FILE.read_text(encoding="utf-8").strip() or None
        if HEARTBEAT_FILE.exists():
            try:
                last = float(HEARTBEAT_FILE.read_text(encoding="utf-8").strip())
                info["heartbeat_age_sec"] = round(time.time() - last, 1)
                info["is_zombie"] = (info["state"] == "running" and
                                    info["heartbeat_age_sec"] > HEARTBEAT_TIMEOUT)
            except (ValueError, OSError):
                pass
        if PID_FILE.exists():
            try:
                info["pid"] = int(PID_FILE.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pass
        return info

    def check(self):
        """Called between jobs — handles pause/stop + sends heartbeat."""
        self.beat()
        cmd = self.get_command()
        if cmd == "stop":
            self.clear_command()
            self.set_state("stopped")
            logger.warning("🛑 STOP signal received.")
            raise SystemExit(0)
        if cmd == "pause":
            self.set_state("paused")
            logger.warning("⏸️  PAUSED. Send 'resume' to continue.")
            while True:
                time.sleep(2)
                self.beat()
                cmd = self.get_command()
                if cmd == "resume":
                    self.clear_command()
                    self.set_state("running")
                    logger.info("▶️  RESUMED.")
                    return
                if cmd == "stop":
                    self.clear_command()
                    self.set_state("stopped")
                    raise SystemExit(0)


controller = Controller()
