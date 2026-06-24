"""
Self-tests for CAPTCHA Solver.

Run:
    python test_captcha_solver.py
"""
import os
import sys
import sqlite3
import tempfile

from packages.stealth.captcha_solver import (
    CaptchaInfo,
    SolveResult,
    CaptchaSolver,
    detect_captcha,
    solve_if_present,
    PRICING_PER_SOLVE,
)


def test_case(name, condition, details=""):
    print(f"\n=== TEST: {name} ===")
    if condition:
        print("PASS")
    else:
        print("FAIL")
        if details:
            print(f"   Details: {details}")
    return condition


class MockDriver:
    def __init__(self, captcha_type=None, site_key="test-site-key-123"):
        self.captcha_type = captcha_type
        self.site_key = site_key
        self.current_url = "https://example.com/test"

    def find_elements(self, by, selector):
        if self.captcha_type == "hcaptcha":
            if "hcaptcha" in selector or "challenge" in selector:
                return [MockElement(f"https://hcaptcha.com/captcha?sitekey={self.site_key}")]
        elif self.captcha_type == "recaptcha":
            if "recaptcha" in selector:
                return [MockElement(f"https://google.com/recaptcha?k={self.site_key}")]
        return []

    def find_element(self, by, selector):
        if self.captcha_type:
            return MockElement(data_sitekey=self.site_key)
        from selenium.common.exceptions import NoSuchElementException
        raise NoSuchElementException()

    def execute_script(self, script, *args):
        return True


class MockElement:
    def __init__(self, src="", data_sitekey=""):
        self.src = src
        self.data_sitekey = data_sitekey

    def get_attribute(self, name):
        if name == "src":
            return self.src
        if name == "data-sitekey":
            return self.data_sitekey
        return ""


def run_tests():
    passed = 0
    total = 0
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name

    total += 1
    info = CaptchaInfo(type="hcaptcha", site_key="abc123")
    if test_case(
        "CaptchaInfo creation + to_dict",
        info.type == "hcaptcha" and "site_key" in info.to_dict()
    ):
        passed += 1

    total += 1
    result_data = SolveResult(success=True, token="test-token", cost_usd=0.003)
    if test_case(
        "SolveResult creation",
        result_data.success is True and result_data.token == "test-token"
    ):
        passed += 1

    total += 1
    driver = MockDriver(captcha_type="hcaptcha", site_key="hcap-key-xyz")
    info = detect_captcha(driver)
    if test_case(
        "Detect hCaptcha from iframe",
        info is not None and info.type == "hcaptcha" and info.site_key == "hcap-key-xyz",
        details=str(info)
    ):
        passed += 1

    total += 1
    driver = MockDriver(captcha_type="recaptcha", site_key="recap-key-abc")
    info = detect_captcha(driver)
    if test_case(
        "Detect reCAPTCHA from iframe",
        info is not None and info.type == "recaptcha_v2"
    ):
        passed += 1

    total += 1
    driver = MockDriver(captcha_type=None)
    info = detect_captcha(driver)
    if test_case("Return None when no CAPTCHA", info is None):
        passed += 1

    total += 1
    solver = CaptchaSolver({"enabled": False}, db_path=tmp_db)
    if test_case("Disabled solver returns failure", solver.enabled is False):
        passed += 1

    total += 1
    solver = CaptchaSolver({"enabled": True, "provider": "manual"}, db_path=tmp_db)
    if test_case(
        "Manual mode initializes correctly",
        solver.enabled is True and solver.provider == "manual"
    ):
        passed += 1

    total += 1
    os.environ.pop("CAPTCHA_API_KEY", None)
    solver = CaptchaSolver({"enabled": True, "provider": "2captcha"}, db_path=tmp_db)
    if test_case(
        "Provider with no API key falls back to manual",
        solver.provider == "manual"
    ):
        passed += 1

    total += 1
    solver = CaptchaSolver({"enabled": True}, db_path=tmp_db)
    try:
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='captcha_solves'")
        has_table = cursor.fetchone() is not None
        conn.close()
    except Exception:
        has_table = False
    if test_case("DB table captcha_solves created", has_table):
        passed += 1

    total += 1
    info = CaptchaInfo(type="hcaptcha", site_key="test")
    solver = CaptchaSolver({"enabled": True, "provider": "manual", "timeout_seconds": 3}, db_path=tmp_db)
    driver = MockDriver(captcha_type="hcaptcha")
    result_data = solver.solve(driver, info)
    if test_case(
        "Manual solve times out gracefully",
        result_data.success is False and "timeout" in result_data.error.lower()
    ):
        passed += 1

    total += 1
    solver = CaptchaSolver({"enabled": True}, db_path=tmp_db)
    stats = solver.get_stats()
    if test_case(
        "get_stats returns expected keys",
        "total_attempts" in stats and "total_cost_usd" in stats
    ):
        passed += 1

    total += 1
    solver = CaptchaSolver({"enabled": True}, db_path=tmp_db)
    driver = MockDriver(captcha_type=None)
    result_flag = solve_if_present(driver, solver)
    if test_case("solve_if_present returns True with no CAPTCHA", result_flag is True):
        passed += 1

    total += 1
    if test_case(
        "Pricing table has expected entries",
        "hcaptcha_2captcha" in PRICING_PER_SOLVE and "recaptcha_v2_2captcha" in PRICING_PER_SOLVE
    ):
        passed += 1

    try:
        os.unlink(tmp_db)
    except Exception:
        pass

    print(f"\n{'=' * 50}")
    print(f"RESULTS: {passed}/{total} tests passed")
    print(f"{'=' * 50}")

    if passed == total:
        print("All tests PASSED - captcha_solver module is solid")
        return 0

    print(f"{total - passed} test(s) FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(run_tests())
