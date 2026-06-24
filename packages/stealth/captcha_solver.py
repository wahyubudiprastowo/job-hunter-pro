"""
CAPTCHA Solver (Phase 3e, Patch 25).

Detects and solves hCaptcha + reCAPTCHA challenges automatically via paid APIs.

Supported providers:
- 2Captcha (recommended): ~$2.99/1000 hCaptcha, ~$1/1000 reCAPTCHA v2
- Anti-Captcha: similar pricing
- Manual fallback: bot waits for user to solve in browser

Used by extractors (LinkedIn, Indeed, Glassdoor) when CAPTCHA detected.
"""
from __future__ import annotations
import os
import re
import time
import sqlite3
from typing import Optional
from dataclasses import dataclass
from datetime import date
from loguru import logger

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


DEFAULT_TIMEOUT = 180
DEFAULT_POLL_INTERVAL = 5
PRICING_PER_SOLVE = {
    "hcaptcha_2captcha": 0.00299,
    "recaptcha_v2_2captcha": 0.001,
    "recaptcha_v3_2captcha": 0.002,
    "image_2captcha": 0.001,
}


@dataclass
class CaptchaInfo:
    """Detected CAPTCHA info."""
    type: str
    site_key: str = ""
    page_url: str = ""
    iframe_present: bool = False

    def to_dict(self):
        return {
            "type": self.type,
            "site_key": self.site_key,
            "page_url": self.page_url,
            "iframe_present": self.iframe_present,
        }


@dataclass
class SolveResult:
    """Result of solve attempt."""
    success: bool
    token: str = ""
    provider: str = ""
    duration_seconds: float = 0
    cost_usd: float = 0
    error: str = ""
    captcha_type: str = ""


def detect_captcha(driver) -> Optional[CaptchaInfo]:
    """Detect CAPTCHA presence on current page."""
    hcaptcha = _detect_hcaptcha(driver)
    if hcaptcha:
        return hcaptcha

    recaptcha = _detect_recaptcha(driver)
    if recaptcha:
        return recaptcha

    return None


def _detect_hcaptcha(driver) -> Optional[CaptchaInfo]:
    """Detect hCaptcha widget."""
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
        if not iframes:
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[title*='challenge']")

        if iframes:
            site_key = ""
            try:
                src = iframes[0].get_attribute("src") or ""
                match = re.search(r"sitekey=([a-f0-9-]+)", src)
                if match:
                    site_key = match.group(1)
            except Exception:
                pass

            if not site_key:
                try:
                    div = driver.find_element(By.CSS_SELECTOR, "div.h-captcha, div[data-sitekey]")
                    site_key = div.get_attribute("data-sitekey") or ""
                except NoSuchElementException:
                    pass

            return CaptchaInfo(
                type="hcaptcha",
                site_key=site_key,
                page_url=driver.current_url,
                iframe_present=True,
            )
    except Exception as e:
        logger.debug(f"hCaptcha detection error: {e}")
    return None


def _detect_recaptcha(driver) -> Optional[CaptchaInfo]:
    """Detect reCAPTCHA v2 widget."""
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        if iframes:
            site_key = ""
            try:
                src = iframes[0].get_attribute("src") or ""
                match = re.search(r"k=([\\w-]+)", src)
                if match:
                    site_key = match.group(1)
            except Exception:
                pass

            if not site_key:
                try:
                    div = driver.find_element(By.CSS_SELECTOR, "div.g-recaptcha, div[data-sitekey]")
                    site_key = div.get_attribute("data-sitekey") or ""
                except NoSuchElementException:
                    pass

            return CaptchaInfo(
                type="recaptcha_v2",
                site_key=site_key,
                page_url=driver.current_url,
                iframe_present=True,
            )
    except Exception as e:
        logger.debug(f"reCAPTCHA detection error: {e}")
    return None


class CaptchaSolver:
    """Main CAPTCHA solver with multi-provider support."""

    def __init__(self, config=None, db_path="data/applications.db"):
        config = config or {}
        self.enabled = config.get("enabled", False)
        self.provider = config.get("provider", "manual").lower()
        self.api_key = os.getenv("CAPTCHA_API_KEY", "") or config.get("api_key", "")
        self.timeout = int(config.get("timeout_seconds", DEFAULT_TIMEOUT))
        self.cost_alert_usd = float(config.get("cost_alert_usd", 5.0))
        self.db_path = db_path

        self._init_db()

        if self.enabled:
            if self.provider == "manual":
                logger.info("CAPTCHA solver: manual mode (user-solves)")
            elif not self.api_key:
                logger.warning(f"CAPTCHA solver: provider={self.provider} but no API key - falling back to manual")
                self.provider = "manual"
            else:
                masked = self.api_key[:6] + "***" + self.api_key[-4:] if len(self.api_key) > 12 else "***"
                logger.success(f"CAPTCHA solver: {self.provider} ready (key: {masked})")

    def _init_db(self):
        """Initialize captcha_solves table."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS captcha_solves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    captcha_type TEXT,
                    provider TEXT,
                    success INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    cost_usd REAL,
                    error TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"captcha_solves table init failed: {e}")

    def solve(self, driver, info: CaptchaInfo) -> SolveResult:
        """Solve detected CAPTCHA."""
        if not self.enabled:
            return SolveResult(
                success=False,
                provider="disabled",
                captcha_type=info.type,
                error="CAPTCHA solver disabled in config",
            )

        start = time.time()

        if self.provider == "2captcha":
            result = self._solve_2captcha(driver, info)
        elif self.provider == "anticaptcha":
            result = self._solve_anticaptcha(driver, info)
        else:
            result = self._solve_manual(driver, info)

        result.duration_seconds = round(time.time() - start, 1)
        result.captcha_type = info.type
        result.provider = self.provider

        self._log_solve(result)

        monthly_cost = self.get_monthly_cost()
        if monthly_cost > self.cost_alert_usd:
            logger.warning(
                f"CAPTCHA monthly cost: ${monthly_cost:.2f} > threshold ${self.cost_alert_usd:.2f}"
            )

        return result

    def _solve_2captcha(self, driver, info: CaptchaInfo) -> SolveResult:
        """Solve via 2Captcha API."""
        try:
            import requests
        except ImportError:
            return SolveResult(success=False, error="requests library not installed")

        if not info.site_key:
            return SolveResult(success=False, error="No site_key found")

        submit_url = "http://2captcha.com/in.php"

        if info.type == "hcaptcha":
            method = "hcaptcha"
        elif info.type == "recaptcha_v2":
            method = "userrecaptcha"
        else:
            return SolveResult(success=False, error=f"Unsupported CAPTCHA type: {info.type}")

        params = {
            "key": self.api_key,
            "method": method,
            "sitekey": info.site_key,
            "pageurl": info.page_url,
            "json": 1,
        }

        try:
            r = requests.post(submit_url, data=params, timeout=30)
            data = r.json()

            if data.get("status") != 1:
                return SolveResult(
                    success=False,
                    error=f"2Captcha submit error: {data.get('request', 'unknown')}",
                )

            captcha_id = data["request"]
            logger.info(f"Submitted to 2Captcha (id={captcha_id}, type={info.type})")

        except Exception as e:
            return SolveResult(success=False, error=f"2Captcha submit failed: {e}")

        result_url = "http://2captcha.com/res.php"
        end = time.time() + self.timeout
        time.sleep(15)

        while time.time() < end:
            try:
                r = requests.get(result_url, params={
                    "key": self.api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1,
                }, timeout=15)
                data = r.json()

                if data.get("status") == 1:
                    token = data["request"]
                    logger.success(f"2Captcha solved (id={captcha_id})")

                    if self._inject_token(driver, info.type, token):
                        return SolveResult(
                            success=True,
                            token=token,
                            cost_usd=PRICING_PER_SOLVE.get(f"{info.type}_2captcha", 0.003),
                        )
                    return SolveResult(
                        success=False,
                        error="Token received but injection failed",
                    )

                if data.get("request") == "CAPCHA_NOT_READY":
                    time.sleep(DEFAULT_POLL_INTERVAL)
                    continue

                return SolveResult(
                    success=False,
                    error=f"2Captcha error: {data.get('request', 'unknown')}",
                )

            except Exception as e:
                logger.debug(f"2Captcha poll error: {e}")
                time.sleep(DEFAULT_POLL_INTERVAL)

        return SolveResult(success=False, error="2Captcha timeout")

    def _solve_anticaptcha(self, driver, info: CaptchaInfo) -> SolveResult:
        """Solve via Anti-Captcha API."""
        try:
            import requests
        except ImportError:
            return SolveResult(success=False, error="requests not installed")

        if not info.site_key:
            return SolveResult(success=False, error="No site_key found")

        task_type = {
            "hcaptcha": "HCaptchaTaskProxyless",
            "recaptcha_v2": "RecaptchaV2TaskProxyless",
        }.get(info.type)

        if not task_type:
            return SolveResult(success=False, error=f"Unsupported: {info.type}")

        try:
            r = requests.post("https://api.anti-captcha.com/createTask", json={
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": info.page_url,
                    "websiteKey": info.site_key,
                }
            }, timeout=30)
            data = r.json()

            if data.get("errorId") != 0:
                return SolveResult(
                    success=False,
                    error=f"Anti-Captcha create error: {data.get('errorDescription')}",
                )

            task_id = data["taskId"]
            logger.info(f"Created Anti-Captcha task (id={task_id})")

        except Exception as e:
            return SolveResult(success=False, error=f"Anti-Captcha create failed: {e}")

        end = time.time() + self.timeout
        time.sleep(15)

        while time.time() < end:
            try:
                r = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }, timeout=15)
                data = r.json()

                if data.get("status") == "ready":
                    sol = data.get("solution", {})
                    token = sol.get("gRecaptchaResponse") or sol.get("token") or ""
                    if token:
                        logger.success(f"Anti-Captcha solved (id={task_id})")
                        if self._inject_token(driver, info.type, token):
                            return SolveResult(success=True, token=token, cost_usd=0.003)

                elif data.get("status") == "processing":
                    time.sleep(DEFAULT_POLL_INTERVAL)
                    continue
                else:
                    return SolveResult(
                        success=False,
                        error=f"Anti-Captcha error: {data.get('errorDescription', 'unknown')}",
                    )

            except Exception as e:
                logger.debug(f"Anti-Captcha poll error: {e}")
                time.sleep(DEFAULT_POLL_INTERVAL)

        return SolveResult(success=False, error="Anti-Captcha timeout")

    def _solve_manual(self, driver, info: CaptchaInfo) -> SolveResult:
        """Wait for user to solve CAPTCHA manually in browser."""
        logger.warning(
            f"Manual CAPTCHA mode - please solve {info.type} in browser within {self.timeout}s"
        )

        end = time.time() + self.timeout
        while time.time() < end:
            check = detect_captcha(driver)
            if not check:
                logger.success("CAPTCHA manually solved")
                return SolveResult(success=True, cost_usd=0)
            time.sleep(2)

        return SolveResult(success=False, error="Manual solve timeout")

    def _inject_token(self, driver, captcha_type: str, token: str) -> bool:
        """Inject solved token into page DOM."""
        try:
            if captcha_type == "hcaptcha":
                js_inject = (
                    "var el = document.querySelector('textarea[name=\"h-captcha-response\"]');"
                    "if (el) el.value = arguments[0];"
                    "var el2 = document.querySelector('textarea[name=\"g-recaptcha-response\"]');"
                    "if (el2) el2.value = arguments[0];"
                )
                driver.execute_script(js_inject, token)

                js_callback = (
                    "if (window.hcaptcha && window.hcaptcha.callback) {"
                    "  try { window.hcaptcha.callback(arguments[0]); } catch(e){}"
                    "}"
                )
                driver.execute_script(js_callback, token)

            elif captcha_type == "recaptcha_v2":
                js_inject = (
                    "var el = document.getElementById('g-recaptcha-response');"
                    "if (el) { el.value = arguments[0]; el.innerHTML = arguments[0]; }"
                )
                driver.execute_script(js_inject, token)

                js_callback = (
                    "var els = document.querySelectorAll('.g-recaptcha');"
                    "els.forEach(function(el) {"
                    "  var cb = el.getAttribute('data-callback');"
                    "  if (cb && window[cb]) { try { window[cb](arguments[0]); } catch(e){} }"
                    "});"
                )
                driver.execute_script(js_callback, token)

            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Token injection failed: {e}")
            return False

    def _log_solve(self, result: SolveResult):
        """Log solve attempt to DB."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO captcha_solves
                (timestamp, date, captcha_type, provider, success, duration_seconds, cost_usd, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(time.time()),
                date.today().strftime("%Y-%m-%d"),
                result.captcha_type,
                result.provider,
                1 if result.success else 0,
                result.duration_seconds,
                result.cost_usd,
                result.error or None,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Log solve failed: {e}")

    def get_stats(self) -> dict:
        """Get solver statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as success_count,
                    AVG(duration_seconds) as avg_duration,
                    SUM(cost_usd) as total_cost,
                    captcha_type,
                    provider
                FROM captcha_solves
                GROUP BY captcha_type, provider
            """)
            rows = cursor.fetchall()

            cursor2 = conn.execute("SELECT COUNT(*), SUM(success), SUM(cost_usd) FROM captcha_solves")
            total, success, cost = cursor2.fetchone()

            conn.close()

            return {
                "total_attempts": total or 0,
                "total_success": success or 0,
                "success_rate": round(success / max(total, 1) * 100, 1) if total else 0,
                "total_cost_usd": round(cost or 0, 4),
                "by_type": [
                    {
                        "type": r[4],
                        "provider": r[5],
                        "total": r[0],
                        "success": r[1],
                        "avg_duration": round(r[2] or 0, 1),
                        "cost": round(r[3] or 0, 4),
                    }
                    for r in rows
                ],
            }
        except Exception as e:
            logger.debug(f"Stats query failed: {e}")
            return {"error": str(e)}

    def get_monthly_cost(self) -> float:
        """Get current month's cost."""
        try:
            month_start = date.today().replace(day=1).strftime("%Y-%m-%d")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT SUM(cost_usd) FROM captcha_solves WHERE date >= ?",
                (month_start,)
            )
            cost = cursor.fetchone()[0]
            conn.close()
            return float(cost or 0)
        except Exception:
            return 0.0


def solve_if_present(driver, solver: CaptchaSolver) -> bool:
    """
    Convenience function for extractors.

    Returns True if CAPTCHA was detected AND solved (or no CAPTCHA found).
    Returns False if CAPTCHA found but solve failed.
    """
    info = detect_captcha(driver)
    if info is None:
        return True

    logger.info(f"CAPTCHA detected: {info.type}")
    result = solver.solve(driver, info)

    if result.success:
        logger.success(
            f"CAPTCHA solved in {result.duration_seconds}s "
            f"(cost: ${result.cost_usd:.4f})"
        )
        return True

    logger.error(f"CAPTCHA solve failed: {result.error}")
    return False
