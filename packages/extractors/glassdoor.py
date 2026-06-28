"""
Glassdoor Extractor (Patch 33, Phase 4b).

Features:
- Login: Email/Password OR Google OAuth
- Region auto-detect via location keyword
- Easy Apply 1-click flow
- Salary parsing -> fit_score boost
- Company rating -> metadata
- Multi-strategy job_id extraction
- Cloudflare support (Patch 31.2)
- Profile management (Patch 32.3)

Architecture: ~75% code reuse from Patch 22 Indeed + LinkedIn patterns.
"""
from __future__ import annotations
import os
import re
import time
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from typing import Optional, Tuple
from loguru import logger

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
    NoSuchFrameException, InvalidSessionIdException, WebDriverException,
)

from packages.extractors.base import BaseExtractor
from packages.core.models import (
    SearchFilters, JobListing, ApplicationResult, ApplyStatus,
    SkipReason, UnansweredQuestion,
)
from packages.core.exceptions import LoginError
from packages.stealth.humanizer import human_sleep, type_human

# Optional imports (Cloudflare handling)
try:
    from packages.extractors.cloudflare_helper import handle_cloudflare_safely
    _HAS_CF_HELPER = True
except ImportError:
    _HAS_CF_HELPER = False
    handle_cloudflare_safely = None

# Optional AI
try:
    from packages.ai.question_bot import answer_question_with_ai, build_candidate_facts
    _HAS_AI = True
except ImportError:
    _HAS_AI = False
    answer_question_with_ai = None
    build_candidate_facts = None

try:
    from rapidfuzz import fuzz
except ImportError:
    class fuzz:
        @staticmethod
        def partial_ratio(a, b): return 100 if a.lower() == b.lower() else 0
        @staticmethod
        def token_set_ratio(a, b): return 100 if a.lower() == b.lower() else 0


# ============================================================
# REGION DETECTION
# ============================================================
GLASSDOOR_REGIONS = {
    "us": "https://www.glassdoor.com",
    "uk": "https://www.glassdoor.co.uk",
    "ca": "https://www.glassdoor.ca",
    "de": "https://www.glassdoor.de",
    "fr": "https://www.glassdoor.fr",
    "sg": "https://www.glassdoor.sg",
    "in": "https://www.glassdoor.co.in",
    "au": "https://www.glassdoor.com.au",
    "nl": "https://www.glassdoor.nl",
    "ie": "https://www.glassdoor.ie",
}

LOCATION_KEYWORDS = {
    "uk": ["london", "manchester", "birmingham", "uk", "united kingdom", "england"],
    "ca": ["toronto", "vancouver", "montreal", "canada", "ontario"],
    "de": ["berlin", "munich", "hamburg", "germany", "deutschland"],
    "fr": ["paris", "lyon", "france"],
    "sg": ["singapore"],
    "in": ["bangalore", "mumbai", "delhi", "india", "hyderabad"],
    "au": ["sydney", "melbourne", "brisbane", "australia"],
    "nl": ["amsterdam", "rotterdam", "netherlands"],
    "ie": ["dublin", "ireland"],
}


def auto_detect_region(location: str) -> str:
    """Auto-detect Glassdoor region based on location keyword."""
    if not location:
        return "us"
    loc_lower = location.lower()
    for region, keywords in LOCATION_KEYWORDS.items():
        if any(kw in loc_lower for kw in keywords):
            return region
    return "us"  # Default fallback


# ============================================================
# SELECTORS — Glassdoor 2026 DOM
# ============================================================
SELECTORS = {
    # ===== LOGIN =====
    "login_email_btn": (By.CSS_SELECTOR, "button[data-test='email-form-button']"),
    "login_email_input": (By.CSS_SELECTOR, "input[name='email']"),
    "login_continue_btn": (By.CSS_SELECTOR, "button[type='submit']"),
    "login_password_input": (By.CSS_SELECTOR, "input[name='password']"),
    "login_submit_btn": (By.CSS_SELECTOR, "button[type='submit']"),
    "login_google_btn": (By.CSS_SELECTOR, "button[data-test='google-button']"),
    "login_facebook_btn": (By.CSS_SELECTOR, "button[data-test='facebook-button']"),
    
    # Login success indicators
    "user_avatar": (By.CSS_SELECTOR, "[data-test='profile-icon']"),
    "user_menu": (
        By.CSS_SELECTOR,
        "[data-test='header-user-menu'], "
        "button[data-test='header-profile-button'], "
        "button[aria-label*='profile' i], "
        "a[href*='/profile/']",
    ),
    
    # ===== SEARCH =====
    "search_keyword": (By.CSS_SELECTOR, "input#sc\\.keyword, input[name='sc.keyword']"),
    "search_location": (By.CSS_SELECTOR, "input#sc\\.location, input[name='sc.location']"),
    "search_submit": (By.CSS_SELECTOR, "button[data-test='search-bar-submit']"),
    
    # ===== JOB CARDS (scoped to results) =====
    "job_list_container": (
        By.CSS_SELECTOR,
        "#MainCol, [data-test='jlGrid'], [data-test='job-listing-module'], "
        "ul[data-test='job-listings'], div[data-test='job-listings'], "
        "[class*='JobsList_jobsList'], [class*='JobsList_jobList']",
    ),
    "job_card": (By.CSS_SELECTOR,
        "li[data-test='jobListing'], "
        "article[data-test='jobListing'], "
        "div[data-test='job-card'], "
        "li[class*='JobsList_jobListItem'], "
        "div[class*='JobsList_jobListItem'], "
        "div.JobsList_jobListItem__JBBUV, "
        "li.react-job-listing"),
    "job_card_link": (By.CSS_SELECTOR,
        "a[data-test='job-link'], "
        "a[class*='JobCard_jobTitle'], "
        "a.JobCard_jobTitle__GLyJ1, "
        "a[href*='jobListingId='], "
        "a[href*='/job-listing/']"),
    "job_card_title": (By.CSS_SELECTOR,
        "a[data-test='job-link'] span, "
        "a[data-test='job-link'], "
        "a[class*='JobCard_jobTitle'], "
        "a.JobCard_jobTitle__GLyJ1, "
        "a[href*='jobListingId='], "
        "a[href*='/job-listing/']"),
    "job_card_company": (By.CSS_SELECTOR,
        "[data-test='employer-name'], "
        "[class*='EmployerProfile_compactEmployerName'], "
        "div.EmployerProfile_compactEmployerName__9MGcV, "
        "[data-test='company-name']"),
    "job_card_location": (By.CSS_SELECTOR,
        "[data-test='emp-location'], "
        "[data-test='location'], "
        "[data-test='job-location'], "
        "[class*='JobCard_location']"),
    "job_card_salary": (By.CSS_SELECTOR,
        "[data-test='detailSalary'], "
        "div[data-test='salary-estimate'], "
        "[class*='JobCard_salaryEstimate']"),
    "job_card_rating": (By.CSS_SELECTOR,
        "[data-test='rating'], "
        "span.EmployerProfile_ratingContainer__N7Z6Y"),
    
    # ===== JOB DETAIL =====
    "detail_title": (By.CSS_SELECTOR, "h1, [data-test='job-title']"),
    "detail_company": (By.CSS_SELECTOR, "[data-test='inflated-employer-name']"),
    "detail_salary": (By.CSS_SELECTOR, "[data-test='detailSalary']"),
    "detail_description": (By.CSS_SELECTOR,
        "[data-test='jobDescriptionText'], "
        "div.JobDetails_jobDescription__uW_fK"),
    "detail_rating": (By.CSS_SELECTOR, "[data-test='employer-rating']"),
    
    # ===== APPLY =====
    "easy_apply_btn": (By.CSS_SELECTOR,
        "button[data-test='easyApply'], "
        "button.applyButton"),
    "external_apply_btn": (By.CSS_SELECTOR,
        "button[data-test='applyButton'], "
        "a[data-test='externalApply']"),
    "apply_btn_xpath": (By.XPATH,
        "//button[contains(., 'Easy Apply') or contains(., 'Apply now')]"),
    
    # ===== APPLY MODAL/IFRAME =====
    "apply_iframe": (By.CSS_SELECTOR,
        "iframe[title*='Apply'], iframe[title*='apply'], "
        "iframe[src*='apply'], iframe[name*='apply'], "
        "iframe#indeedapply-modal-content, "
        "iframe.ia-IFrame"),
    "apply_modal": (By.CSS_SELECTOR,
        "div[data-test='application-modal'], "
        "div.application-container"),
    "apply_continue_btn": (By.XPATH,
        "//button[contains(., 'Continue') or contains(., 'Next') "
        "or contains(., 'Review')]"),
    "apply_submit_btn": (By.XPATH,
        "//button[contains(., 'Submit Application') "
        "or contains(., 'Submit application') "
        "or contains(., 'Send Application') "
        "or normalize-space(.)='Submit']"),
    
    # Verification (applied)
    "applied_indicator": (By.XPATH,
        "//*[contains(text(), 'Application submitted') or "
        "contains(text(), 'Thanks for applying') or "
        "contains(text(), 'Your application has been sent')]"),
    
    # Sign in prompt overlay
    "sign_in_prompt": (By.CSS_SELECTOR,
        "div[data-test='modal-content'] button[data-test='sign-in-button']"),
    "modal_close": (By.CSS_SELECTOR,
        "button[data-test='modal-close'], "
        "button.SVGInline-svg-close, "
        "button[aria-label='Close'], "
        "button[aria-label='close'], "
        "button[data-test='close-button']"),
}


# Date filter codes
DATE_CODE = {
    "past_24h": "1",
    "past_3d": "3",
    "past_week": "7",
    "past_14d": "14",
    "past_month": "30",
    "any": "",
}


# ============================================================
# SALARY PARSER (for fit scoring boost)
# ============================================================
def parse_salary(salary_text: str) -> dict:
    """
    Parse Glassdoor salary string into structured data.
    
    Examples:
    - "$120K - $150K (Glassdoor est.)"
    - "S$100K - S$140K Per Year"
    - "$80,000 - $100,000"
    
    Returns: {min, max, currency, period, is_estimated}
    """
    if not salary_text:
        return {"min": None, "max": None, "currency": None, "period": "year", "is_estimated": False, "raw": ""}
    
    result = {
        "raw": salary_text,
        "min": None,
        "max": None,
        "currency": "USD",
        "period": "year",
        "is_estimated": "est" in salary_text.lower(),
    }
    
    # Currency detection
    currency_map = {
        "$": "USD", "S$": "SGD", "£": "GBP", "€": "EUR",
        "C$": "CAD", "A$": "AUD", "₹": "INR",
    }
    for sym, cur in currency_map.items():
        if sym in salary_text:
            result["currency"] = cur
            break
    
    # Extract numbers (handle K notation)
    matches = re.findall(r"(\d+(?:[,.]\d+)*)\s*([Kk])?", salary_text)
    numbers = []
    for num_str, k_suffix in matches:
        try:
            num = float(num_str.replace(",", "").replace(".", ""))
            if k_suffix.lower() == "k":
                num *= 1000
            numbers.append(num)
        except ValueError:
            continue
    
    if numbers:
        result["min"] = int(min(numbers))
        result["max"] = int(max(numbers))
    
    # Period detection
    text_lower = salary_text.lower()
    if "hour" in text_lower or "/hr" in text_lower:
        result["period"] = "hour"
    elif "month" in text_lower or "/mo" in text_lower:
        result["period"] = "month"
    
    return result


def salary_to_annual_usd(salary_data: dict) -> Optional[int]:
    """Convert parsed salary to annual USD equivalent for comparison."""
    if not salary_data.get("max"):
        return None
    
    amount = salary_data["max"]
    
    # Convert to annual
    if salary_data.get("period") == "hour":
        amount *= 2080  # 40 hr/week × 52 weeks
    elif salary_data.get("period") == "month":
        amount *= 12
    
    # Convert currency to USD (rough approximations)
    rates = {
        "USD": 1.0, "SGD": 0.74, "GBP": 1.27, "EUR": 1.07,
        "CAD": 0.73, "AUD": 0.65, "INR": 0.012,
    }
    rate = rates.get(salary_data.get("currency", "USD"), 1.0)
    return int(amount * rate)

# ============================================================
# GLASSDOOR EXTRACTOR CLASS
# ============================================================
class GlassdoorExtractor(BaseExtractor):
    """
    Glassdoor job extractor.
    
    Per user decisions:
    - Login: Both Email/Password AND Google OAuth
    - Region: Auto-detect via location
    - Apply: Easy Apply only
    - Salary: Use for fit scoring boost
    """
    name = "glassdoor"
    requires_login = True
    supports_easy_apply = True
    
    def __init__(self, driver, config, profile, answer_bank, stealth_cfg,
                 ai_provider=None, ai_config=None, cv_text=None,
                 captcha_solver=None):
        super().__init__(driver, config, profile, answer_bank, stealth_cfg)
        
        # Auto-detect region from search location
        location = config.get("search", {}).get("location", "")
        region = config.get("region", "")
        if not region or region == "auto":
            region = auto_detect_region(location)
        
        self.region = region
        self.base_url = GLASSDOOR_REGIONS.get(region, GLASSDOOR_REGIONS["us"])
        logger.info(f"Glassdoor region: {region} -> {self.base_url}")
        
        # Credentials
        self.email = os.getenv("GLASSDOOR_EMAIL", "")
        self.password = os.getenv("GLASSDOOR_PASSWORD", "")
        self.login_method = config.get("login_method", "auto")  # auto | email | google
        self._last_search_time = 0.0
        self.pause_current_run = False
        self.pause_reason = ""
        
        # AI question fallback
        self.ai_provider = ai_provider
        self.ai_config = ai_config or {}
        self.cv_text = cv_text or ""
        self.captcha_solver = captcha_solver
        
        # Candidate facts for AI questions
        self.candidate_facts = None
        if _HAS_AI and ai_provider and build_candidate_facts:
            try:
                self.candidate_facts = build_candidate_facts(profile, answer_bank, cv_text)
                logger.info("AI question fallback enabled for Glassdoor.")
            except Exception as e:
                logger.debug(f"Build candidate_facts failed: {e}")
        
        # Apply tracking
        self._applied_in_run = 0
    
    # ============================================================
    # LOGIN
    # ============================================================
    def login(self, email="", password="", totp_secret=""):
        """Login to Glassdoor via Email or Google OAuth (auto-detect)."""
        d = self.driver
        
        # Use credentials from env or args
        email = email or self.email
        password = password or self.password
        
        # Step 1: Visit homepage
        d.get(self.base_url)
        human_sleep(2, 4)

        # Prefer an existing browser session before invoking challenge handling.
        if self._has_active_session():
            logger.success("Already logged in to Glassdoor.")
            return
        
        # Step 2: Check Glassdoor security challenge
        if self._is_security_page():
            if not self._wait_for_security_clearance(self.base_url):
                logger.warning("=" * 60)
                logger.warning("Glassdoor verification could not be cleared.")
                logger.warning("Run: python scripts/prewarm_glassdoor.py")
                logger.warning("=" * 60)
                raise LoginError("Glassdoor security blocked - run prewarm script")
            human_sleep(2, 4)
        
        # Step 3: Check if already logged in (cookie persists)
        if self._has_active_session():
            logger.success("Already logged in to Glassdoor.")
            return
        
        # Step 4: Click "Sign in" button
        try:
            sign_in_btn = d.find_element(
                By.XPATH,
                "//button[contains(., 'Sign in') or contains(., 'Sign In')]"
            )
            sign_in_btn.click()
            human_sleep(2, 4)
        except NoSuchElementException:
            if self._is_security_page():
                if self._wait_for_security_clearance(self.base_url):
                    if self._has_active_session():
                        logger.success("Already logged in to Glassdoor after verification.")
                        return
                    logger.warning("Glassdoor verification cleared, but login controls were not visible.")
                    return
                raise LoginError("Glassdoor security page is still active - run prewarm script")
            logger.warning("Sign in button not found, proceeding with current Glassdoor session/page")
            return
        
        # Step 5: Decide login method
        # AUTO: Try Google first if available, fallback Email
        method = self.login_method
        if method == "auto":
            try:
                d.find_element(*SELECTORS["login_google_btn"])
                method = "google"
            except NoSuchElementException:
                method = "email"
        
        if method == "google":
            self._login_via_google()
        else:
            self._login_via_email(email, password)
        
        # Verify login success
        try:
            WebDriverWait(d, 30).until(
                EC.presence_of_element_located(SELECTORS["user_avatar"])
            )
            logger.success(f"Logged in to Glassdoor as {email or '(via OAuth)'}")
        except TimeoutException:
            raise LoginError("Glassdoor login verification timeout")

    def _has_active_session(self) -> bool:
        """Best-effort check for an already usable Glassdoor session."""
        if self._is_security_page():
            return False
        try:
            checks = [
                SELECTORS["user_avatar"],
                SELECTORS["user_menu"],
                (By.CSS_SELECTOR, "a[href*='member/home']"),
                (By.CSS_SELECTOR, "a[href*='profile/index']"),
                (By.XPATH, "//*[contains(., 'Sign Out') or contains(., 'My Account')]"),
            ]
            for selector in checks:
                try:
                    if self.driver.find_elements(*selector):
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False
    
    def _login_via_google(self):
        """Login via Google OAuth (uses Chrome profile session)."""
        d = self.driver
        logger.info("Attempting Glassdoor login via Google OAuth...")
        
        try:
            btn = d.find_element(*SELECTORS["login_google_btn"])
            btn.click()
            human_sleep(3, 5)
            
            # If Chrome profile has Google session, OAuth auto-redirects
            # Otherwise user needs to login Google manually
            logger.info("Waiting for Google OAuth (use Chrome profile with Google login)...")
            
            # Wait up to 60s for redirect back to Glassdoor logged-in state
            WebDriverWait(d, 60).until(
                lambda drv: "glassdoor" in drv.current_url.lower()
                and "/auth/" not in drv.current_url.lower()
            )
            human_sleep(2, 4)
        except TimeoutException:
            raise LoginError("Google OAuth timeout - login Google manually first")
        except NoSuchElementException:
            raise LoginError("Google OAuth button not found on Glassdoor")
    
    def _login_via_email(self, email: str, password: str):
        """Login via Email + Password form."""
        d = self.driver
        
        if not email or not password:
            raise LoginError("Glassdoor email/password missing in .env")
        
        logger.info(f"Attempting Glassdoor login via email: {email}")
        
        # Step 1: Click "Continue with Email" button if exists
        try:
            email_btn = d.find_element(*SELECTORS["login_email_btn"])
            email_btn.click()
            human_sleep(1, 2)
        except NoSuchElementException:
            pass  # Already on email form
        
        # Step 2: Enter email
        try:
            email_input = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["login_email_input"])
            )
            email_input.clear()
            type_human(email_input, email)
            human_sleep(0.5, 1.5)
        except TimeoutException:
            raise LoginError("Glassdoor email input not found")
        
        # Step 3: Click continue
        try:
            continue_btn = d.find_element(*SELECTORS["login_continue_btn"])
            continue_btn.click()
            human_sleep(2, 4)
        except NoSuchElementException:
            pass
        
        # Step 4: Enter password
        try:
            password_input = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["login_password_input"])
            )
            password_input.clear()
            type_human(password_input, password)
            human_sleep(0.5, 1.5)
        except TimeoutException:
            raise LoginError("Glassdoor password input not found")
        
        # Step 5: Submit
        try:
            submit_btn = d.find_element(*SELECTORS["login_submit_btn"])
            submit_btn.click()
            human_sleep(3, 6)
        except NoSuchElementException:
            password_input.submit()
            human_sleep(3, 6)
    
    # ============================================================
    # SEARCH
    # ============================================================
    def _build_search_url(self, query: str, filters: SearchFilters) -> str:
        """Build Glassdoor search URL."""
        normalized_query = " ".join((query or "").split())
        slug = re.sub(r"[^a-z0-9]+", "-", normalized_query.lower()).strip("-") or "jobs"
        url = (
            f"{self.base_url}/Job/{slug}-jobs-"
            f"SRCH_KO0%2C{len(normalized_query)}.htm"
        )
        params = {}
        
        # Date filter
        if filters.date_posted in DATE_CODE and DATE_CODE[filters.date_posted]:
            params["fromAge"] = DATE_CODE[filters.date_posted]
        
        # Easy Apply only
        if filters.easy_apply_only:
            params["applicationType"] = "1"
        
        # When remote and hybrid are both enabled, keep all work modes and let
        # the shared location guard accept the configured market.
        if filters.remote and not filters.hybrid:
            params["remoteWorkType"] = "1"
        
        encoded = urlencode({k: v for k, v in params.items() if v})
        return f"{url}?{encoded}" if encoded else url

    def _current_url_lower(self) -> str:
        try:
            return (self.driver.current_url or "").lower()
        except (InvalidSessionIdException, WebDriverException):
            return ""

    def _on_community_page(self) -> bool:
        return "/community/" in self._current_url_lower()

    def _on_jobs_or_results_page(self) -> bool:
        current = self._current_url_lower()
        return "/job/" in current or "/job-listing/" in current

    def _open_jobs_navigation(self) -> bool:
        """Open the visible Jobs navigation item from pages such as Community."""
        try:
            links = self.driver.find_elements(
                By.XPATH,
                "//a[normalize-space()='Jobs' or contains(@href, '/Job/') "
                "or contains(@href, '/Search/')]",
            )
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    if not link.is_displayed():
                        continue
                    suffix = f": {href}" if href else ""
                    logger.info(f"Glassdoor opening Jobs navigation{suffix}.")
                    try:
                        link.click()
                    except (ElementClickInterceptedException, WebDriverException):
                        self.driver.execute_script("arguments[0].click();", link)
                    human_sleep(3, 5)
                    return self._on_jobs_or_results_page()
                except (StaleElementReferenceException, WebDriverException):
                    continue
        except (InvalidSessionIdException, WebDriverException):
            return False
        return False

    def _restore_job_search_url(self, url: str, reason: str) -> bool:
        """Force Glassdoor back to the Jobs/Search page after redirects."""
        try:
            if self._on_community_page():
                self._open_jobs_navigation()
            logger.info(f"Glassdoor {reason}: opening Jobs search URL: {url}")
            self.driver.get(url)
            human_sleep(4, 6)
            if self._on_community_page():
                logger.info("Glassdoor returned to Community; retrying through the Jobs navigation.")
                self._open_jobs_navigation()
                self.driver.get(url)
                human_sleep(4, 6)
            if self._on_community_page():
                self.pause_current_run = True
                self.pause_reason = "Glassdoor redirected to Community instead of Jobs"
                logger.warning(
                    f"{self.pause_reason}. Open the Jobs tab once in this profile, "
                    "then rerun the Glassdoor scrape."
                )
                return False
            return True
        except (InvalidSessionIdException, WebDriverException) as e:
            self.pause_current_run = True
            self.pause_reason = "Glassdoor browser session closed while navigating to Jobs"
            logger.warning(f"{self.pause_reason}: {e}")
            return False

    def _try_interactive_search(self, query: str, filters: SearchFilters) -> bool:
        """Use the visible Glassdoor search form before falling back to direct URLs."""
        d = self.driver
        try:
            d.get(self.base_url)
            human_sleep(2, 4)
            if self._is_security_page():
                return False
            if self._on_community_page():
                logger.info("Glassdoor opened Community page; falling back to direct Jobs URL.")
                return False

            keyword = WebDriverWait(d, 8).until(
                EC.presence_of_element_located(SELECTORS["search_keyword"])
            )
            keyword.send_keys(Keys.CONTROL, "a")
            keyword.send_keys(Keys.BACKSPACE)
            type_human(keyword, query)

            try:
                location = d.find_element(*SELECTORS["search_location"])
                location.send_keys(Keys.CONTROL, "a")
                location.send_keys(Keys.BACKSPACE)
                type_human(location, filters.location or "")
            except NoSuchElementException:
                pass

            try:
                submit = d.find_element(*SELECTORS["search_submit"])
                submit.click()
            except NoSuchElementException:
                keyword.send_keys(Keys.ENTER)

            human_sleep(4, 6)
            return True
        except Exception as e:
            logger.debug(f"Glassdoor interactive search unavailable, falling back to URL: {e}")
            return False

    def _is_security_page(self) -> bool:
        """Detect Glassdoor anti-bot/security pages that replace real search results."""
        try:
            title = (self.driver.title or "").lower()
        except Exception:
            title = ""
        try:
            visible_text = (self.driver.find_element(By.TAG_NAME, "body").text or "").lower()
        except Exception:
            visible_text = ""
        current_url = self._current_url_lower()
        security_url = any(
            marker in current_url
            for marker in ("/challenge", "/captcha", "/blocked", "/security-check")
        )
        security_text = any(
            marker in visible_text
            for marker in (
                "verify you are human",
                "additional verification required",
                "checking your browser",
                "access denied",
                "complete the security check",
            )
        )
        return (
            "security | glassdoor" in title
            or "just a moment" in title
            or security_url
            or security_text
        )

    def _has_job_card_nodes(self) -> bool:
        """Return True when the current page has visible job-result anchors/cards."""
        try:
            if self.driver.find_elements(*SELECTORS["job_card"]):
                return True
            if self.driver.find_elements(By.CSS_SELECTOR, "a[href*='jobListingId='], a[href*='/job-listing/']"):
                return True
        except Exception:
            return False
        return False

    def _dismiss_overlays(self) -> None:
        """Close Glassdoor prompts that cover the Jobs list."""
        try:
            close_buttons = self.driver.find_elements(*SELECTORS["modal_close"])
            for button in close_buttons:
                try:
                    if not button.is_displayed():
                        continue
                    self.driver.execute_script("arguments[0].click();", button)
                    human_sleep(0.5, 1)
                    return
                except (StaleElementReferenceException, WebDriverException):
                    continue

            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ESCAPE)
            human_sleep(0.5, 1)
        except (InvalidSessionIdException, WebDriverException, NoSuchElementException):
            pass

    def _wait_for_security_clearance(self, return_to_url: str, timeout: int | None = None) -> bool:
        """Let the user solve Glassdoor verification manually, then restore the search URL."""
        wait_seconds = int(timeout or self.config.get("security_wait_timeout", 300) or 300)
        logger.warning("=" * 70)
        logger.warning("GLASSDOOR SECURITY / VERIFICATION DETECTED")
        logger.warning("=" * 70)
        logger.warning("Action in the opened browser:")
        logger.warning("  1. Complete the Glassdoor verification manually")
        logger.warning("  2. Make sure you are logged in on the SAME region/domain")
        logger.warning(f"  3. Bot will wait up to {max(1, wait_seconds // 60)} minute(s)")
        logger.warning(f"Target domain: {self.base_url}")
        logger.warning("=" * 70)

        end = time.time() + wait_seconds
        while time.time() < end:
            if self._has_job_card_nodes():
                logger.success("Glassdoor job cards visible after verification.")
                return True

            if not self._is_security_page():
                try:
                    current_url = self.driver.current_url or ""
                except (InvalidSessionIdException, WebDriverException) as e:
                    self.pause_current_run = True
                    self.pause_reason = "Glassdoor browser session closed during verification"
                    logger.warning(f"{self.pause_reason}: {e}")
                    return False
                if self.base_url in current_url and ("/Job/" in current_url or "/Search/" in current_url):
                    logger.success("Glassdoor verification cleared on search/results page.")
                    return True
                return_lower = (return_to_url or "").lower()
                if "/job/" in return_lower or "/search/" in return_lower:
                    if not self._restore_job_search_url(return_to_url, "verification cleared"):
                        return False
                    if self._has_job_card_nodes() or not self._is_security_page():
                        return True
                else:
                    logger.success("Glassdoor verification cleared.")
                    return True

            time.sleep(5)

        logger.error(f"Glassdoor verification wait timeout after {wait_seconds}s")
        return False
    
    def search(self, filters: SearchFilters):
        """Execute search."""
        self.pause_current_run = False
        self.pause_reason = ""
        if not filters.queries:
            return False
        q = filters.queries[0]
        url = self._build_search_url(q, filters)
        logger.info(f"Glassdoor search: {q} -> {url}")
        if not self._restore_job_search_url(url, "search"):
            return False
        
        if self._is_security_page() and not self._has_job_card_nodes():
            if self._wait_for_security_clearance(url):
                human_sleep(2, 3)
                if not self._restore_job_search_url(url, "after verification"):
                    return False
            else:
                self.pause_current_run = True
                self.pause_reason = "Glassdoor search landed on a security/verification page"
                logger.warning(
                    "Glassdoor search landed on a security/verification page. "
                    f"Current URL: {self.driver.current_url}"
                )
                logger.warning(
                    "Prewarm the SAME Glassdoor region/domain used by the bot "
                    f"({self.base_url}) and ensure that profile is already verified/logged in."
                )
                return False

        if self._on_community_page():
            if not self._restore_job_search_url(url, "redirected to Community"):
                return False

        if not self._on_jobs_or_results_page():
            self.pause_current_run = True
            self.pause_reason = "Glassdoor search did not open a Jobs results page"
            logger.warning(
                f"{self.pause_reason}. Current URL: {self.driver.current_url}"
            )
            return False

        self._dismiss_overlays()
        return True
    
    # ============================================================
    # COLLECT JOB CARDS
    # ============================================================
    def collect_job_cards(self, max_cards: int = 50) -> list:
        """Collect job cards from Glassdoor search results."""
        d = self.driver
        cards = []
        seen = set()

        self._dismiss_overlays()

        if self._is_security_page():
            self.pause_current_run = True
            self.pause_reason = "Glassdoor results page is blocked by a security challenge"
            logger.warning(
                "Glassdoor results page is blocked by a security challenge, "
                "so no job cards can be collected."
            )
            return cards
        
        # Wait for results container
        try:
            WebDriverWait(d, 15).until(
                EC.presence_of_element_located(SELECTORS["job_list_container"])
            )
        except TimeoutException:
            logger.warning("Glassdoor job list container not found - trying direct card scan")
        
        # Scroll for lazy load
        scroll_count = self.config.get("scroll_count", 8)
        for _ in range(scroll_count):
            d.execute_script("window.scrollBy(0, 800);")
            human_sleep(1.0, 2.0)
            
            # Click "Show more" button if exists
            try:
                show_more = d.find_element(
                    By.XPATH,
                    "//button[@data-test='load-more' "
                    "or contains(normalize-space(.), 'Show more jobs') "
                    "or contains(normalize-space(.), 'Load more jobs')]"
                )
                if show_more.is_displayed() and show_more.is_enabled():
                    d.execute_script("arguments[0].click();", show_more)
                    human_sleep(1, 2)
            except (NoSuchElementException, StaleElementReferenceException, WebDriverException):
                pass
        
        # Find cards
        nodes = d.find_elements(*SELECTORS["job_card"])
        if not nodes:
            nodes = self._collect_job_card_links_fallback()
        logger.info(f"Found {len(nodes)} Glassdoor job card nodes.")
        
        for idx, node in enumerate(nodes[:max_cards]):
            try:
                jid = self._extract_job_id(node)
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                
                # Extract salary
                salary_text = self._safe_text(node, SELECTORS["job_card_salary"])
                salary_data = parse_salary(salary_text) if salary_text else {}
                
                # Extract rating
                rating = self._extract_rating(node)
                
                card = {
                    "job_id": jid,
                    "title": self._safe_text(node, SELECTORS["job_card_title"]),
                    "company": self._safe_text(node, SELECTORS["job_card_company"]),
                    "location": self._safe_text(node, SELECTORS["job_card_location"]),
                    "salary": salary_text,
                    "salary_parsed": salary_data,
                    "company_rating": rating,
                    "url": self._extract_card_url(node),
                    "_element": node,
                }
                cards.append(card)
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.debug(f"Card {idx} error: {e}")
                continue
        
        logger.info(f"Collected {len(cards)} unique Glassdoor cards.")
        return cards
    
    def _extract_job_id(self, node) -> Optional[str]:
        """Multi-strategy job_id extraction."""
        # Strategy 1: data-jobid attribute
        try:
            jid = node.get_attribute("data-jobid") or node.get_attribute("data-job-listing-id")
            if jid:
                return jid
        except Exception:
            pass

        # Strategy 1b: node itself is already the job link
        try:
            href = node.get_attribute("href") or ""
            m = re.search(r"jobListingId=(\d+)", href)
            if m:
                return m.group(1)
            m = re.search(r"[?&]jl=(\d+)", href)
            if m:
                return m.group(1)
            m = re.search(r"jl(\d+)\.htm", href)
            if m:
                return m.group(1)
        except Exception:
            pass
        
        # Strategy 2: extract from link href
        try:
            link = node.find_element(*SELECTORS["job_card_link"])
            href = link.get_attribute("href") or ""
            # /partner/jobListing.htm?jobListingId=1234567890
            m = re.search(r"jobListingId=(\d+)", href)
            if m:
                return m.group(1)
            m = re.search(r"[?&]jl=(\d+)", href)
            if m:
                return m.group(1)
            # /job-listing/title-jl1234567890.htm
            m = re.search(r"jl(\d+)\.htm", href)
            if m:
                return m.group(1)
        except Exception:
            pass
        
        return None
    
    def _extract_card_url(self, node) -> str:
        """Extract job URL from card."""
        try:
            if (node.tag_name or "").lower() == "a":
                return node.get_attribute("href") or ""
            link = node.find_element(*SELECTORS["job_card_link"])
            return link.get_attribute("href") or ""
        except Exception:
            return ""

    def _collect_job_card_links_fallback(self) -> list:
        """Fallback when the main list container/selector changes but links still exist."""
        try:
            links = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[href*='jobListingId='], a[href*='/job-listing/']",
            )
            nodes = []
            seen = set()
            for link in links:
                candidate = link
                try:
                    candidate = link.find_element(
                        By.XPATH,
                        "./ancestor::*[self::li or self::article "
                        "or @data-test='jobListing' "
                        "or contains(@class, 'JobsList_jobListItem')][1]"
                    )
                except Exception:
                    try:
                        candidate = link.find_element(By.XPATH, "./ancestor::div[1]")
                    except Exception:
                        candidate = link
                try:
                    key = candidate.id
                except Exception:
                    key = id(candidate)
                if key in seen:
                    continue
                seen.add(key)
                nodes.append(candidate)
            logger.debug(f"Glassdoor fallback found {len(nodes)} card/link candidates.")
            return nodes
        except Exception:
            return []
    
    def _extract_rating(self, node) -> Optional[float]:
        """Extract company rating (1-5 stars)."""
        try:
            rating_el = node.find_element(*SELECTORS["job_card_rating"])
            text = rating_el.text.strip()
            m = re.search(r"(\d\.\d)", text)
            if m:
                return float(m.group(1))
        except Exception:
            pass
        return None
    
    def _safe_text(self, parent, selector):
        """Safe text extraction."""
        try:
            if (parent.tag_name or "").lower() == "a":
                direct = (
                    parent.text.strip()
                    or (parent.get_attribute("title") or "").strip()
                    or (parent.get_attribute("aria-label") or "").strip()
                )
                if direct:
                    return direct
            elem = parent.find_element(*selector)
            return (
                elem.text.strip()
                or (elem.get_attribute("title") or "").strip()
                or (elem.get_attribute("aria-label") or "").strip()
            )
        except (NoSuchElementException, Exception):
            return ""
    
    # ============================================================
    # OPEN JOB DETAIL
    # ============================================================
    def open_job_detail(self, card) -> JobListing:
        """Open job detail and return JobListing."""
        d = self.driver

        # Use the card URL so title/company/detail always belong to the same job.
        card_url = (card.get("url") or "").strip()
        try:
            if card_url:
                d.get(card_url)
            else:
                element = card.get("_element")
                if not element:
                    raise ValueError("Glassdoor card has no URL or element")
                try:
                    link = element.find_element(*SELECTORS["job_card_link"])
                    d.execute_script("arguments[0].click();", link)
                except Exception:
                    d.execute_script("arguments[0].click();", element)
            human_sleep(2, 4)
        except Exception as e:
            logger.warning(f"Open Glassdoor job URL failed: {e}")
            if card_url:
                d.get(card_url)
                human_sleep(2, 4)
        
        # Dismiss sign-in prompt if appears
        try:
            close = d.find_element(*SELECTORS["modal_close"])
            close.click()
            human_sleep(0.5, 1)
        except NoSuchElementException:
            pass
        
        # Extract details
        detail_title = self._safe_text_global(SELECTORS["detail_title"])
        if re.match(r"^\s*\d[\d,]*\s+.+\s+jobs?\s+in\s+", detail_title, re.IGNORECASE):
            detail_title = ""
        title = card.get("title", "") or detail_title
        company = card.get("company", "") or self._safe_text_global(SELECTORS["detail_company"])
        description = self._safe_text_global(SELECTORS["detail_description"]) or ""
        salary = card.get("salary", "")
        
        url = card_url or d.current_url
        
        # Check if Easy Apply
        is_easy_apply = self.can_auto_apply_check()
        
        return JobListing(
            platform="glassdoor",
            job_id=card["job_id"],
            title=title,
            company=company,
            location=card.get("location", ""),
            url=url,
            description=description,
            salary=salary,
            is_easy_apply=is_easy_apply,
            raw={
                "platform": "glassdoor",
                "salary_parsed": card.get("salary_parsed", {}),
                "company_rating": card.get("company_rating"),
                "region": self.region,
            },
        )
    
    def _safe_text_global(self, selector):
        """Safe text from full document."""
        try:
            elem = self.driver.find_element(*selector)
            return elem.text.strip()
        except (NoSuchElementException, Exception):
            return ""
    
    # ============================================================
    # APPLY DETECTION & ACTION
    # ============================================================
    def can_auto_apply_check(self) -> bool:
        """Check if Easy Apply available on current page."""
        try:
            self.driver.find_element(*SELECTORS["easy_apply_btn"])
            return True
        except NoSuchElementException:
            pass
        
        # Try XPath fallback
        try:
            btn = self.driver.find_element(*SELECTORS["apply_btn_xpath"])
            btn_text = btn.text.lower()
            return "easy apply" in btn_text
        except NoSuchElementException:
            return False
    
    def can_auto_apply(self, job: JobListing) -> bool:
        """BaseExtractor interface."""
        return job.is_easy_apply
    
    def apply(self, job: JobListing, resume_path: str = "", mode: str = "full_auto",
              cover_letter_paths: dict | None = None) -> ApplicationResult:
        """Apply to Glassdoor job."""
        d = self.driver
        qa_log: list[dict] = []
        unanswered: list[UnansweredQuestion] = []
        cover_letter_used = None
        handles_before = set(d.window_handles)

        try:
            try:
                apply_btn = d.find_element(*SELECTORS["easy_apply_btn"])
            except NoSuchElementException:
                apply_btn = d.find_element(*SELECTORS["apply_btn_xpath"])

            d.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
            human_sleep(0.4, 0.8)
            try:
                apply_btn.click()
            except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
                d.execute_script("arguments[0].click();", apply_btn)
            human_sleep(2, 4)
        except NoSuchElementException:
            return ApplicationResult(
                status=ApplyStatus.EXTERNAL,
                error_message="No Easy Apply button found",
            )

        self._switch_to_new_apply_window(handles_before)
        if not self._switch_to_apply_context():
            self._save_apply_debug(job.job_id, "form_not_found")
            return ApplicationResult(
                status=ApplyStatus.FAILED,
                error_message="Glassdoor Easy Apply form not found after click",
            )

        previous_signature = ""
        for step in range(12):
            self._switch_to_apply_context()
            logger.info(f"Glassdoor Apply step {step + 1}")

            self._upload_apply_files(resume_path, cover_letter_paths)
            cover_letter_used = self._fill_cover_letter_text(cover_letter_paths) or cover_letter_used
            step_unanswered = self._fill_apply_fields(qa_log, job)
            unanswered = self._merge_unanswered(unanswered, step_unanswered)

            if step_unanswered:
                logger.warning(
                    f"Glassdoor Apply needs {len(step_unanswered)} answer(s) at step {step + 1}"
                )
                self._save_apply_debug(job.job_id, f"needs_answers_step{step + 1}")
                return ApplicationResult(
                    status=ApplyStatus.NEEDS_ANSWERS,
                    error_message="Unanswered Glassdoor question(s)",
                    qa_log=qa_log,
                    unanswered_questions=unanswered,
                    resume_path=resume_path or None,
                    cover_letter_path=cover_letter_used,
                )

            if self._click_visible_button(SELECTORS["apply_submit_btn"]):
                human_sleep(3, 5)
                if self._verify_applied():
                    self._applied_in_run += 1
                    return ApplicationResult(
                        status=ApplyStatus.APPLIED,
                        qa_log=qa_log,
                        unanswered_questions=unanswered,
                        resume_path=resume_path or None,
                        cover_letter_path=cover_letter_used,
                    )
                self._save_apply_debug(job.job_id, "submit_unverified")
                return ApplicationResult(
                    status=ApplyStatus.FAILED,
                    error_message="Submit clicked but Glassdoor confirmation was not found",
                    qa_log=qa_log,
                    unanswered_questions=unanswered,
                    resume_path=resume_path or None,
                    cover_letter_path=cover_letter_used,
                )

            if self._click_visible_button(SELECTORS["apply_continue_btn"]):
                human_sleep(2, 4)
                continue

            signature = self._apply_page_signature()
            if self._verify_applied():
                self._applied_in_run += 1
                return ApplicationResult(
                    status=ApplyStatus.APPLIED,
                    qa_log=qa_log,
                    resume_path=resume_path or None,
                    cover_letter_path=cover_letter_used,
                )
            if signature == previous_signature:
                self._save_apply_debug(job.job_id, f"stuck_step{step + 1}")
                break
            previous_signature = signature

        return ApplicationResult(
            status=ApplyStatus.FAILED,
            error_message="Glassdoor Apply has no Continue or Submit action",
            qa_log=qa_log,
            unanswered_questions=unanswered,
            resume_path=resume_path or None,
            cover_letter_path=cover_letter_used,
        )

    def _switch_to_new_apply_window(self, handles_before: set[str]) -> bool:
        end = time.time() + 10
        while time.time() < end:
            try:
                new_handles = [h for h in self.driver.window_handles if h not in handles_before]
                if new_handles:
                    self.driver.switch_to.window(new_handles[0])
                    human_sleep(1, 2)
                    logger.info("Switched to new Glassdoor Apply tab/window")
                    return True
            except WebDriverException:
                return False
            time.sleep(0.5)
        return False

    def _has_apply_form_markers(self) -> bool:
        selectors = (
            "input[type='file'], input[type='text'], input[type='email'], "
            "input[type='tel'], textarea, select, "
            "[data-testid*='apply'], [data-test*='apply'], "
            "[class*='application'], [class*='Application']"
        )
        try:
            if any(el.is_displayed() for el in self.driver.find_elements(By.CSS_SELECTOR, selectors)):
                return True
            body = (self.driver.find_element(By.TAG_NAME, "body").text or "").lower()
            return any(
                marker in body
                for marker in ("submit application", "continue application", "upload resume")
            )
        except WebDriverException:
            return False

    def _switch_to_apply_context(self) -> bool:
        try:
            self.driver.switch_to.default_content()
        except WebDriverException:
            return False

        if self._has_apply_form_markers():
            return True

        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        except WebDriverException:
            return False
        for frame in frames:
            try:
                attrs = " ".join(
                    frame.get_attribute(name) or ""
                    for name in ("id", "name", "title", "src", "class")
                ).lower()
                if not any(token in attrs for token in ("apply", "indeed", "smartapply", "ia-")):
                    continue
                self.driver.switch_to.frame(frame)
                if self._has_apply_form_markers():
                    logger.debug("Glassdoor Apply form found inside iframe")
                    return True
                self.driver.switch_to.default_content()
            except (NoSuchFrameException, StaleElementReferenceException, WebDriverException):
                try:
                    self.driver.switch_to.default_content()
                except WebDriverException:
                    pass
        return False

    def _upload_apply_files(self, resume_path: str, cover_letter_paths: dict | None) -> None:
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        except WebDriverException:
            return
        for file_input in inputs:
            try:
                label = self._label_for(file_input).lower()
                name = (file_input.get_attribute("name") or "").lower()
                marker = f"{label} {name}"
                target = None
                if "cover" in marker and cover_letter_paths:
                    target = cover_letter_paths.get("pdf") or cover_letter_paths.get("txt")
                elif resume_path:
                    target = resume_path
                if target:
                    absolute = os.path.abspath(target)
                    if os.path.exists(absolute):
                        file_input.send_keys(absolute)
                        logger.debug(f"Glassdoor uploaded file: {os.path.basename(absolute)}")
            except (StaleElementReferenceException, WebDriverException):
                continue

    def _fill_cover_letter_text(self, cover_letter_paths: dict | None) -> Optional[str]:
        if not cover_letter_paths or not cover_letter_paths.get("txt"):
            return None
        path = cover_letter_paths["txt"]
        if not os.path.exists(path):
            return None
        content = Path(path).read_text(encoding="utf-8")
        for textarea in self.driver.find_elements(By.TAG_NAME, "textarea"):
            try:
                if "cover" not in self._label_for(textarea).lower():
                    continue
                if not (textarea.get_attribute("value") or "").strip():
                    textarea.send_keys(content)
                return path
            except (StaleElementReferenceException, WebDriverException):
                continue
        return None

    def _fill_apply_fields(self, qa_log: list[dict], job: JobListing) -> list[UnansweredQuestion]:
        unanswered: list[UnansweredQuestion] = []
        text_selector = (
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='number'], textarea"
        )
        for element in self.driver.find_elements(By.CSS_SELECTOR, text_selector):
            try:
                if not element.is_displayed() or (element.get_attribute("value") or "").strip():
                    continue
                label = self._label_for(element)
                answer = self._lookup_answer(label, "text")
                if answer is None:
                    if self._is_required(element):
                        unanswered.append(self._unanswered(job, label, "text"))
                        qa_log.append({"q": label, "a": None, "filled": False})
                    continue
                element.clear()
                type_human(element, str(answer))
                qa_log.append({"q": label, "a": str(answer), "filled": True})
            except (StaleElementReferenceException, WebDriverException):
                continue

        for element in self.driver.find_elements(By.TAG_NAME, "select"):
            try:
                if not element.is_displayed():
                    continue
                select = Select(element)
                options = [o.text.strip() for o in select.options if o.text.strip()]
                if element.get_attribute("value") not in ("", None):
                    continue
                label = self._label_for(element)
                answer = self._lookup_answer(label, "select", options)
                if answer is None:
                    if self._is_required(element):
                        unanswered.append(self._unanswered(job, label, "select", options))
                    continue
                best = max(
                    options,
                    key=lambda option: fuzz.partial_ratio(option.lower(), str(answer).lower()),
                    default=None,
                )
                if best:
                    select.select_by_visible_text(best)
                    qa_log.append({"q": label, "a": best, "filled": True})
            except (StaleElementReferenceException, WebDriverException):
                continue

        seen_names: set[str] = set()
        for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
            try:
                if not radio.is_displayed():
                    continue
                name = radio.get_attribute("name") or ""
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                group = self.driver.find_elements(By.CSS_SELECTOR, f"input[name='{name}']")
                if any(option.is_selected() for option in group):
                    continue
                labels = [self._label_for(option) or (option.get_attribute("value") or "") for option in group]
                question = self._label_for_radio_group(name)
                answer = self._lookup_answer(question, "radio", labels)
                if answer is None:
                    unanswered.append(self._unanswered(job, question, "radio", labels))
                    continue
                best_index = max(
                    range(len(labels)),
                    key=lambda i: fuzz.partial_ratio(labels[i].lower(), str(answer).lower()),
                    default=None,
                )
                if best_index is not None:
                    self.driver.execute_script("arguments[0].click();", group[best_index])
                    qa_log.append({"q": question, "a": labels[best_index], "filled": True})
            except (StaleElementReferenceException, WebDriverException):
                continue

        for checkbox in self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            try:
                if not checkbox.is_displayed() or checkbox.is_selected():
                    continue
                label = self._label_for(checkbox).lower()
                if any(token in label for token in ("agree", "consent", "privacy", "terms", "certify", "confirm")):
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    qa_log.append({"q": label, "a": "checked", "filled": True})
                elif self._is_required(checkbox):
                    unanswered.append(self._unanswered(job, label, "checkbox"))
            except (StaleElementReferenceException, WebDriverException):
                continue
        return unanswered

    def _label_for(self, element) -> str:
        try:
            element_id = element.get_attribute("id")
            if element_id:
                labels = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{element_id}']")
                if labels and labels[0].text.strip():
                    return labels[0].text.strip()
        except WebDriverException:
            pass
        try:
            parent = element.find_element(By.XPATH, "ancestor::label[1]")
            if parent.text.strip():
                return parent.text.strip()
        except (NoSuchElementException, WebDriverException):
            pass
        return (
            element.get_attribute("aria-label")
            or element.get_attribute("placeholder")
            or element.get_attribute("name")
            or "(unknown)"
        ).strip()

    def _label_for_radio_group(self, name: str) -> str:
        try:
            fieldset = self.driver.find_element(
                By.XPATH, f"//input[@name='{name}']/ancestor::fieldset[1]"
            )
            legend = fieldset.find_element(By.TAG_NAME, "legend")
            if legend.text.strip():
                return legend.text.strip()
        except (NoSuchElementException, WebDriverException):
            pass
        return name or "(unknown)"

    def _lookup_answer(self, question: str, field_type: str, options: list[str] | None = None):
        normalized = (question or "").strip().lower()
        if not normalized:
            return None
        try:
            for key, value in self.profile.as_field_map().items():
                if key in normalized and value:
                    return value
        except Exception:
            pass
        for key, value in self.answer_bank.items():
            candidate = str(key).strip().lower()
            if candidate == normalized or candidate in normalized or normalized in candidate:
                return value
        best_score, best_value = 0, None
        for key, value in self.answer_bank.items():
            score = fuzz.token_set_ratio(normalized, str(key).lower())
            if score > best_score:
                best_score, best_value = score, value
        if best_score >= 85:
            return best_value
        if (
            _HAS_AI
            and self.ai_provider
            and self.ai_provider.is_available()
            and self.ai_config.get("question_fallback", False)
            and self.candidate_facts
        ):
            try:
                return answer_question_with_ai(
                    self.ai_provider,
                    question,
                    self.candidate_facts,
                    field_type=field_type,
                    options=options,
                    system_prompt_template=self.ai_config.get("system_prompt") or None,
                )
            except Exception as e:
                logger.warning(f"Glassdoor AI answer fallback failed: {e}")
        return None

    @staticmethod
    def _is_required(element) -> bool:
        return bool(
            element.get_attribute("required") is not None
            or (element.get_attribute("aria-required") or "").lower() == "true"
        )

    def _unanswered(
        self,
        job: JobListing,
        question: str,
        field_type: str,
        options: list[str] | None = None,
    ) -> UnansweredQuestion:
        return UnansweredQuestion(
            question=question or "(unknown)",
            field_type=field_type,
            options=options or [],
            job_id=job.job_id,
            platform=self.name,
        )

    @staticmethod
    def _merge_unanswered(
        existing: list[UnansweredQuestion],
        incoming: list[UnansweredQuestion],
    ) -> list[UnansweredQuestion]:
        merged = list(existing)
        seen = {(item.question, item.field_type) for item in merged}
        for item in incoming:
            key = (item.question, item.field_type)
            if key not in seen:
                seen.add(key)
                merged.append(item)
        return merged

    def _click_visible_button(self, selector) -> bool:
        for button in self.driver.find_elements(*selector):
            try:
                if not button.is_displayed() or not button.is_enabled():
                    continue
                try:
                    button.click()
                except (ElementClickInterceptedException, WebDriverException):
                    self.driver.execute_script("arguments[0].click();", button)
                return True
            except (StaleElementReferenceException, WebDriverException):
                continue
        return False

    def _apply_page_signature(self) -> str:
        try:
            return "|".join(
                [
                    self.driver.current_url or "",
                    self.driver.title or "",
                    (self.driver.find_element(By.TAG_NAME, "body").text or "")[:500],
                ]
            )
        except WebDriverException:
            return ""

    def _save_apply_debug(self, job_id: str, suffix: str) -> None:
        try:
            output = Path("data/screenshots")
            output.mkdir(parents=True, exist_ok=True)
            path = output / f"glassdoor_{suffix}_{job_id}_{int(time.time())}.png"
            self.driver.save_screenshot(str(path))
            logger.info(f"Glassdoor apply debug screenshot: {path}")
        except Exception:
            pass
    
    def _verify_applied(self) -> bool:
        """Check if applied indicator appeared."""
        try:
            self.driver.find_element(*SELECTORS["applied_indicator"])
            return True
        except NoSuchElementException:
            return False
    
    def close(self):
        """Cleanup."""
        return None
