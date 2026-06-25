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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
    NoSuchFrameException,
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
    "user_menu": (By.CSS_SELECTOR, "[data-test='header-user-menu']"),
    
    # ===== SEARCH =====
    "search_keyword": (By.CSS_SELECTOR, "input#sc\\.keyword, input[name='sc.keyword']"),
    "search_location": (By.CSS_SELECTOR, "input#sc\\.location, input[name='sc.location']"),
    "search_submit": (By.CSS_SELECTOR, "button[data-test='search-bar-submit']"),
    
    # ===== JOB CARDS (scoped to results) =====
    "job_list_container": (By.CSS_SELECTOR, "#MainCol, [data-test='jlGrid']"),
    "job_card": (By.CSS_SELECTOR,
        "li[data-test='jobListing'], "
        "div[data-test='job-card'], "
        "div.JobsList_jobListItem__JBBUV"),
    "job_card_link": (By.CSS_SELECTOR,
        "a[data-test='job-link'], "
        "a.JobCard_jobTitle__GLyJ1"),
    "job_card_title": (By.CSS_SELECTOR,
        "a[data-test='job-link'] span, "
        "a[data-test='job-link']"),
    "job_card_company": (By.CSS_SELECTOR,
        "[data-test='employer-name'], "
        "div.EmployerProfile_compactEmployerName__9MGcV"),
    "job_card_location": (By.CSS_SELECTOR,
        "[data-test='emp-location'], "
        "[data-test='location']"),
    "job_card_salary": (By.CSS_SELECTOR,
        "[data-test='detailSalary'], "
        "div[data-test='salary-estimate']"),
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
        "iframe[title*='Apply'], "
        "iframe#indeedapply-modal-content, "
        "iframe.ia-IFrame"),
    "apply_modal": (By.CSS_SELECTOR,
        "div[data-test='application-modal'], "
        "div.application-container"),
    "apply_continue_btn": (By.XPATH,
        "//button[contains(., 'Continue') or contains(., 'Next')]"),
    "apply_submit_btn": (By.XPATH,
        "//button[contains(., 'Submit') or contains(., 'Send Application')]"),
    
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
        "button.SVGInline-svg-close"),
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
        
        # AI question fallback
        self.ai_provider = ai_provider
        self.ai_config = ai_config or {}
        self.cv_text = cv_text or ""
        self.captcha_solver = captcha_solver
        
        # Candidate facts for AI questions
        self.candidate_facts = None
        if _HAS_AI and ai_provider and build_candidate_facts:
            try:
                self.candidate_facts = build_candidate_facts(profile, cv_text)
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
        
        # Step 2: Check Cloudflare
        if _HAS_CF_HELPER and handle_cloudflare_safely:
            if not handle_cloudflare_safely(d, timeout=180):
                logger.warning("=" * 60)
                logger.warning("Glassdoor Cloudflare could not be cleared.")
                logger.warning("Run: python scripts/prewarm_glassdoor.py")
                logger.warning("=" * 60)
                raise LoginError("Cloudflare blocked - run prewarm script")
        
        # Step 3: Check if already logged in (cookie persists)
        try:
            d.find_element(*SELECTORS["user_avatar"])
            logger.success("Already logged in to Glassdoor.")
            return
        except NoSuchElementException:
            pass
        
        # Step 4: Click "Sign in" button
        try:
            sign_in_btn = d.find_element(
                By.XPATH,
                "//button[contains(., 'Sign in') or contains(., 'Sign In')]"
            )
            sign_in_btn.click()
            human_sleep(2, 4)
        except NoSuchElementException:
            logger.warning("Sign in button not found, may already be logged in")
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
        params = {
            "sc.keyword": query,
            "locT": "C",  # City
            "sc.location": filters.location or "",
        }
        
        # Date filter
        if filters.date_posted in DATE_CODE and DATE_CODE[filters.date_posted]:
            params["fromAge"] = DATE_CODE[filters.date_posted]
        
        # Easy Apply only
        if filters.easy_apply_only:
            params["applicationType"] = "1"
        
        # Remote
        if filters.remote:
            params["remoteWorkType"] = "1"
        
        encoded = urlencode({k: v for k, v in params.items() if v})
        return f"{self.base_url}/Job/jobs.htm?{encoded}"
    
    def search(self, filters: SearchFilters):
        """Execute search."""
        if not filters.queries:
            return
        q = filters.queries[0]
        url = self._build_search_url(q, filters)
        logger.info(f"Glassdoor search: {q} -> {url}")
        self.driver.get(url)
        human_sleep(3, 5)
        
        # Handle Cloudflare if appears
        if _HAS_CF_HELPER and handle_cloudflare_safely:
            handle_cloudflare_safely(self.driver, timeout=60)
        
        # Dismiss any sign-in prompt overlay
        try:
            close_btn = self.driver.find_element(*SELECTORS["modal_close"])
            close_btn.click()
            human_sleep(1, 2)
        except NoSuchElementException:
            pass
    
    # ============================================================
    # COLLECT JOB CARDS
    # ============================================================
    def collect_job_cards(self, max_cards: int = 50) -> list:
        """Collect job cards from Glassdoor search results."""
        d = self.driver
        cards = []
        seen = set()
        
        # Wait for results container
        try:
            WebDriverWait(d, 15).until(
                EC.presence_of_element_located(SELECTORS["job_list_container"])
            )
        except TimeoutException:
            logger.warning("Glassdoor job list container not found")
            return cards
        
        # Scroll for lazy load
        scroll_count = self.config.get("scroll_count", 8)
        for _ in range(scroll_count):
            d.execute_script("window.scrollBy(0, 800);")
            human_sleep(1.0, 2.0)
            
            # Click "Show more" button if exists
            try:
                show_more = d.find_element(
                    By.XPATH,
                    "//button[contains(., 'Show more') or contains(., 'Load more')]"
                )
                show_more.click()
                human_sleep(1, 2)
            except NoSuchElementException:
                pass
        
        # Find cards
        nodes = d.find_elements(*SELECTORS["job_card"])
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
        
        # Strategy 2: extract from link href
        try:
            link = node.find_element(*SELECTORS["job_card_link"])
            href = link.get_attribute("href") or ""
            # /partner/jobListing.htm?jobListingId=1234567890
            m = re.search(r"jobListingId=(\d+)", href)
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
            link = node.find_element(*SELECTORS["job_card_link"])
            return link.get_attribute("href") or ""
        except Exception:
            return ""
    
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
            elem = parent.find_element(*selector)
            return elem.text.strip()
        except (NoSuchElementException, Exception):
            return ""
    
    # ============================================================
    # OPEN JOB DETAIL
    # ============================================================
    def open_job_detail(self, card) -> JobListing:
        """Open job detail and return JobListing."""
        d = self.driver
        
        # Click card to open detail in right panel
        try:
            element = card.get("_element")
            if element:
                try:
                    element.click()
                except Exception:
                    d.execute_script("arguments[0].click();", element)
            else:
                # Fallback: navigate to URL
                d.get(card["url"])
            human_sleep(2, 4)
        except Exception as e:
            logger.warning(f"Click card failed: {e}")
            # Try direct navigation
            if card.get("url"):
                d.get(card["url"])
                human_sleep(2, 4)
        
        # Dismiss sign-in prompt if appears
        try:
            close = d.find_element(*SELECTORS["modal_close"])
            close.click()
            human_sleep(0.5, 1)
        except NoSuchElementException:
            pass
        
        # Extract details
        title = self._safe_text_global(SELECTORS["detail_title"]) or card.get("title", "")
        company = self._safe_text_global(SELECTORS["detail_company"]) or card.get("company", "")
        description = self._safe_text_global(SELECTORS["detail_description"]) or ""
        salary = self._safe_text_global(SELECTORS["detail_salary"]) or card.get("salary", "")
        
        # Build URL
        url = d.current_url
        
        # Check if Easy Apply
        is_easy_apply = self.can_auto_apply_check()
        
        return JobListing(
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
              cover_letter_path: str = "") -> ApplicationResult:
        """Apply to Glassdoor job."""
        d = self.driver
        
        # Find and click Easy Apply button
        try:
            try:
                apply_btn = d.find_element(*SELECTORS["easy_apply_btn"])
            except NoSuchElementException:
                apply_btn = d.find_element(*SELECTORS["apply_btn_xpath"])
            
            apply_btn.click()
            human_sleep(2, 4)
        except NoSuchElementException:
            return ApplicationResult(
                status=ApplyStatus.EXTERNAL,
                error_message="No Easy Apply button found",
            )
        
        # Switch to iframe if present (Glassdoor often uses iframe)
        switched_iframe = False
        try:
            iframe = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["apply_iframe"])
            )
            d.switch_to.frame(iframe)
            switched_iframe = True
            human_sleep(2, 3)
        except TimeoutException:
            pass  # No iframe, modal in main page
        
        # Click Continue/Next until reach Submit
        try:
            max_steps = 10
            for step in range(max_steps):
                human_sleep(1, 2)
                
                # Try Submit first
                try:
                    submit_btn = d.find_element(*SELECTORS["apply_submit_btn"])
                    submit_btn.click()
                    human_sleep(3, 5)
                    
                    # Verify applied
                    if self._verify_applied():
                        self._applied_in_run += 1
                        if switched_iframe:
                            d.switch_to.default_content()
                        return ApplicationResult(
                            status=ApplyStatus.APPLIED,
                            message="Applied via Glassdoor Easy Apply",
                        )
                except NoSuchElementException:
                    pass
                
                # Try Continue/Next
                try:
                    next_btn = d.find_element(*SELECTORS["apply_continue_btn"])
                    next_btn.click()
                    human_sleep(1, 2)
                except NoSuchElementException:
                    break
        finally:
            if switched_iframe:
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
        
        # If we reach here without applied state, mark needs_answers
        return ApplicationResult(
            status=ApplyStatus.NEEDS_ANSWERS,
            message="Apply form requires manual answers",
        )
    
    def _verify_applied(self) -> bool:
        """Check if applied indicator appeared."""
        try:
            self.driver.find_element(*SELECTORS["applied_indicator"])
            return True
        except NoSuchElementException:
            return False
    
    def close(self):
        """Cleanup."""
        try:
            self.driver.quit()
        except Exception:
            pass