"""
Indeed Extractor (Phase 4a, Patch 22).

Implements BaseExtractor interface for Indeed.com.

Features:
- Login with cached session via Chrome profile
- Search with Indeed-specific filters (q, l, sc, fromage)
- Job card collection with lazy scroll
- Detail extraction
- Indeed Apply (1-click) detection
- Indeed Apply flow (uses iframe)
- External apply detection (redirect to company site)
- Multi-strategy "Apply now" button detection
- Rate limit awareness (integrates with Patch 19)

Limitations:
- hCaptcha appears occasionally - needs manual solve OR 2Captcha (Phase 3e)
- Indeed Apply iframe has nested DOM (handled via switch_to.frame)
"""
from __future__ import annotations
import os
import time
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from loguru import logger
from rapidfuzz import fuzz

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
    NoSuchFrameException, ElementNotInteractableException,
)

from packages.extractors.base import BaseExtractor
from packages.extractors.indeed_2026_fixes import (
    INDEED_SELECTORS_2026,
    apply_stealth_javascript,
    build_search_url_2026,
    collect_job_cards_2026,
)
from packages.extractors.cloudflare_helper import (
    detect_cloudflare_state,
    handle_cloudflare_safely,
)
from packages.extractors.indeed_v2_fixes import (
    INDEED_SELECTORS_V2,
    _extract_title_v2,
    build_indeed_url_v2,
    collect_indeed_cards_v2,
)
from packages.extractors.robust_click import robust_click
from packages.core.models import (
    SearchFilters, JobListing, ApplicationResult, ApplyStatus,
    SkipReason, UnansweredQuestion,
)
from packages.core.exceptions import LoginError
from packages.stealth.humanizer import human_sleep, type_human

try:
    from packages.ai.question_bot import answer_question_with_ai, build_candidate_facts
    _HAS_AI = True
except ImportError:
    _HAS_AI = False
    answer_question_with_ai = None
    build_candidate_facts = None


BTN_APPLY_NOW = [
    "Apply now", "Apply on company site", "Easily apply",
    "Apply via Indeed", "Quick apply",
    "Postuler maintenant",
    "Jetzt bewerben",
    "Candidatura",
    "Postular ahora",
    "Solicitar agora",
    "Nu solliciteren",
]

BTN_CONTINUE = [
    "Continue", "Next", "Submit", "Submit application", "Review",
    "Continuer", "Weiter", "Avanti", "Continuar", "Volgende",
]

BTN_SUBMIT = [
    "Submit application", "Submit", "Send application",
    "Envoyer la candidature", "Bewerbung absenden",
    "Invia candidatura", "Enviar solicitud", "Verstuur sollicitatie",
]


def _xpath_button_any(labels):
    """Build XPath for button matching any of the labels."""
    conds = []
    for lbl in labels:
        conds.append(f"normalize-space(.)='{lbl}'")
        conds.append(f"contains(., '{lbl}')")
        conds.append(f".//span[contains(., '{lbl}')]")
    return "//button[" + " or ".join(conds) + "]"


SELECTORS = {
    "login_email": (By.ID, "ifl-InputFormField-ihl-useId-passport-webapp-1"),
    "login_email_alt": (By.CSS_SELECTOR, "input[type='email'], input[name='__email']"),
    "login_continue": (By.XPATH, "//button[contains(., 'Continue') or contains(., 'Sign in')]"),
    "login_password": (By.CSS_SELECTOR, "input[type='password']"),
    "login_submit": (By.XPATH, "//button[@type='submit']"),
    "search_input": (By.ID, "text-input-what"),
    "location_input": (By.ID, "text-input-where"),
    "search_submit": (By.XPATH, "//button[@type='submit' and contains(., 'Find jobs')]"),
    "job_card": (
        By.CSS_SELECTOR,
        "div[data-testid='slider_item'], td.resultContent, li[data-jk], "
        "div.job_seen_beacon, div[data-jk], li.css-1ac2h1w",
    ),
    "job_card_link": (By.CSS_SELECTOR, "h2.jobTitle a, a[data-jk], a.jcs-JobTitle"),
    "job_card_title": (
        By.CSS_SELECTOR,
        "h2.jobTitle span[title], h2.jobTitle a span, h2.jobTitle, [data-testid='job-title']",
    ),
    "job_card_company": (
        By.CSS_SELECTOR,
        "[data-testid='company-name'], span.companyName, .companyName, [data-testid*='company']",
    ),
    "job_card_location": (
        By.CSS_SELECTOR,
        "[data-testid='text-location'], .companyLocation, [data-testid*='location']",
    ),
    "detail_title": (By.CSS_SELECTOR, "h1.jobsearch-JobInfoHeader-title, h2.jobsearch-JobInfoHeader-title"),
    "detail_company": (By.CSS_SELECTOR, "div[data-company-name='true'], .jobsearch-CompanyInfoContainer"),
    "detail_location": (By.CSS_SELECTOR, "div[data-testid='inlineHeader-companyLocation']"),
    "detail_description": (By.CSS_SELECTOR, "div#jobDescriptionText, .jobsearch-jobDescriptionText"),
    "detail_salary": (By.CSS_SELECTOR, "div#salaryInfoAndJobType, span[data-testid='salaryInfo']"),
    "apply_now_btn": (By.XPATH, _xpath_button_any(BTN_APPLY_NOW)),
    "indeed_apply_btn": (By.CSS_SELECTOR, "button#indeedApplyButton, button.ia-IndeedApplyButton"),
    "external_apply_indicator": (By.XPATH, "//button[contains(., 'Apply on company site') or contains(., 'company website')]"),
    "ia_iframe": (By.CSS_SELECTOR, "iframe[title*='Apply'], iframe#indeedapply-modal-content, iframe.ia-IFrame"),
    "ia_continue_btn": (By.XPATH, _xpath_button_any(BTN_CONTINUE)),
    "ia_submit_btn": (By.XPATH, _xpath_button_any(BTN_SUBMIT)),
    "ia_resume_upload": (By.CSS_SELECTOR, "input[type='file'][name*='resume'], input[type='file']"),
    "ia_text_input": (By.CSS_SELECTOR, "input[type='text'], input[type='number'], textarea"),
    "ia_select": (By.TAG_NAME, "select"),
    "ia_radio": (By.CSS_SELECTOR, "input[type='radio']"),
    "ia_checkbox": (By.CSS_SELECTOR, "input[type='checkbox']"),
    "submitted_indicator": (
        By.XPATH,
        "//*[contains(text(),'Application submitted') or "
        "contains(text(),'Thanks for applying') or "
        "contains(text(),'Your application has been submitted')]"
    ),
    "hcaptcha_iframe": (By.CSS_SELECTOR, "iframe[src*='hcaptcha'], iframe[title*='challenge']"),
    "hcaptcha_checkbox": (By.CSS_SELECTOR, "#checkbox"),
}
SELECTORS.update(INDEED_SELECTORS_2026)
SELECTORS.update(INDEED_SELECTORS_V2)


DATE_CODE = {
    "past_24h": "1",
    "past_3d": "3",
    "past_week": "7",
    "past_14d": "14",
    "past_month": "30",
    "any": "",
}

EXP_CODE = {
    "Entry level": "entry_level",
    "Mid level": "mid_level",
    "Senior level": "senior_level",
}


REGION_HOST_ALIASES = {
    "singapore": "sg",
    "germany": "de",
    "deutschland": "de",
    "france": "fr",
    "italy": "it",
    "spain": "es",
    "portugal": "pt",
    "netherlands": "nl",
    "belgium": "be",
    "ireland": "ie",
    "indonesia": "id",
    "saudi arabia": "sa",
    "united kingdom": "uk",
    "great britain": "uk",
}

INDEED_REGION_KEYWORDS = {
    "sg": ["singapore"],
    "uk": ["uk", "united kingdom", "great britain", "london", "manchester", "birmingham"],
    "de": ["germany", "deutschland", "berlin", "munich", "hamburg"],
    "fr": ["france", "paris", "lyon"],
    "ca": ["canada", "toronto", "vancouver", "montreal"],
    "au": ["australia", "sydney", "melbourne", "brisbane"],
    "in": ["india", "bangalore", "mumbai", "delhi", "hyderabad"],
    "nl": ["netherlands", "amsterdam", "rotterdam"],
    "ie": ["ireland", "dublin"],
}


def _resolve_indeed_base_url(region: str, search_location: str = "") -> str:
    raw = (region or "").strip().lower()
    location = (search_location or "").strip().lower()

    if raw in {"", "auto", "global"}:
        inferred = ""
        for alias, keywords in INDEED_REGION_KEYWORDS.items():
            if any(keyword in location for keyword in keywords):
                inferred = alias
                break
        raw = inferred or "us"

    token = REGION_HOST_ALIASES.get(raw, raw)
    token = token.replace("https://", "").replace("http://", "").strip("/")

    if token in {"indeed.com", "www.indeed.com", "www", "us"}:
        return "https://www.indeed.com"
    if token.endswith(".indeed.com"):
        return f"https://{token}"
    if token.replace("-", "").isalnum() and len(token) <= 3:
        return f"https://{token}.indeed.com"

    logger.warning(
        f"Unknown Indeed region '{region}' - falling back to https://www.indeed.com"
    )
    return "https://www.indeed.com"


class IndeedExtractor(BaseExtractor):
    """
    Indeed job extractor.

    Implements BaseExtractor interface for Indeed.com.
    """
    name = "indeed"
    base_url = "https://www.indeed.com"
    requires_login = True
    supports_easy_apply = True

    def __init__(self, driver, config, profile, answer_bank, stealth_cfg,
                 ai_provider=None, ai_config=None, cv_text=None,
                 captcha_solver=None):
        super().__init__(driver, config, profile, answer_bank, stealth_cfg)
        self.ai = ai_provider
        self.ai_cfg = ai_config or {}
        self.captcha_solver = captcha_solver
        self._candidate_facts = None
        self._cv_text = cv_text
        self._answers_file = Path("data/answers.json")
        self._last_detection_failure = None

        search_cfg = config.get("search", {}) or {}
        self.base_url = _resolve_indeed_base_url(
            config.get("region", ""),
            search_cfg.get("location", ""),
        )
        logger.info(f"Indeed base URL resolved to {self.base_url}")
        self._last_search_time = 0.0
        self.pause_current_run = False
        self.pause_reason = ""

        if self.ai and _HAS_AI:
            try:
                self._candidate_facts = build_candidate_facts(profile, answer_bank, self._cv_text)
                logger.info("AI question fallback enabled for Indeed.")
            except Exception as e:
                logger.warning(f"AI fact build failed: {e}")

    def _is_logged_in_session(self) -> bool:
        """
        Best-effort detection for an already-authenticated Indeed session.

        We keep this conservative: account/settings pages and explicit sign-out
        affordances count as authenticated; a generic homepage does not.
        """
        current_url = (self.driver.current_url or "").lower()
        if (
            ("myjobs" in current_url)
            or ("/account/" in current_url and "login" not in current_url)
            or ("profile.indeed.com" in current_url)
        ):
            return True

        checks = [
            (By.CSS_SELECTOR, "a[href*='/account/settings']"),
            (By.CSS_SELECTOR, "a[href*='/account/logout']"),
            (By.CSS_SELECTOR, "a[href*='/myjobs']"),
            (By.XPATH, "//*[contains(., 'Sign out') or contains(., 'Account settings')]"),
        ]
        for by, value in checks:
            try:
                if self.driver.find_elements(by, value):
                    return True
            except Exception:
                continue
        return False

    def _open_with_region_fallback(self, path: str):
        target = f"{self.base_url}{path}"
        try:
            self.driver.get(target)
            return
        except Exception as e:
            if "ERR_NAME_NOT_RESOLVED" in str(e) and self.base_url != "https://www.indeed.com":
                logger.warning(
                    f"Indeed host failed to resolve ({self.base_url}) - retrying on https://www.indeed.com"
                )
                self.base_url = "https://www.indeed.com"
                self.driver.get(f"{self.base_url}{path}")
                return
            raise

    def login(self, email, password, totp_secret=""):
        """
        Login to Indeed.

        Note: Indeed login uses single-page-app flow:
        1. Enter email -> Continue
        2. May redirect to password page
        3. Enter password -> Sign in
        4. Possible hCaptcha challenge
        """
        d = self.driver
        try:
            apply_stealth_javascript(d)
        except Exception as e:
            logger.debug(f"Indeed stealth JS apply skipped: {e}")

        self._open_with_region_fallback("/")
        human_sleep(2, 4)
        if not handle_cloudflare_safely(d, timeout=300, return_to_url=f"{self.base_url}/"):
            logger.warning("=" * 60)
            logger.warning("Indeed Cloudflare could not be cleared.")
            logger.warning("Run: python scripts\\prewarm_indeed.py")
            logger.warning("Complete Cloudflare manually, close browser, then retry.")
            logger.warning("=" * 60)
            raise LoginError("Cloudflare blocked - run prewarm script")

        if self._is_logged_in_session():
            logger.info("Already logged in to Indeed.")
            return True

        self._open_with_region_fallback("/account/login")
        human_sleep(2, 4)
        if not handle_cloudflare_safely(d, timeout=300, return_to_url=f"{self.base_url}/account/login"):
            logger.warning("=" * 60)
            logger.warning("Indeed Cloudflare could not be cleared.")
            logger.warning("Run: python scripts\\prewarm_indeed.py")
            logger.warning("Complete Cloudflare manually, close browser, then retry.")
            logger.warning("=" * 60)
            raise LoginError("Cloudflare blocked - run prewarm script")

        if self._is_logged_in_session():
            logger.info("Already logged in to Indeed.")
            return True

        if not email or not password:
            raise LoginError("Indeed credentials missing and no active session found")

        try:
            email_el = WebDriverWait(d, 15).until(
                EC.presence_of_element_located(SELECTORS["login_email_alt"]))
            type_human(email_el, email,
                       self.stealth_cfg["typing_min_delay"],
                       self.stealth_cfg["typing_max_delay"])
            human_sleep(0.5, 1.0)
        except TimeoutException:
            if self._is_logged_in_session():
                logger.info("Indeed session detected after login redirect.")
                return True
            logger.error("Indeed login email field not found")
            raise LoginError("Indeed login form unavailable")

        try:
            cont_btn = d.find_element(*SELECTORS["login_continue"])
            cont_btn.click()
            human_sleep(2, 4)
        except NoSuchElementException:
            pass

        if self._check_captcha():
            logger.warning("Indeed hCaptcha detected at login - attempting solver or manual fallback")
            self._wait_for_manual_captcha()

        try:
            pwd_el = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["login_password"]))
            type_human(pwd_el, password,
                       self.stealth_cfg["typing_min_delay"],
                       self.stealth_cfg["typing_max_delay"])
            human_sleep(0.5, 1.0)
            d.find_element(*SELECTORS["login_submit"]).click()
        except TimeoutException:
            logger.warning("Indeed password field not found - may use magic link")

        end = time.time() + 120
        while time.time() < end:
            url = d.current_url.lower()
            if "myjobs" in url or "/jobs" in url or ("/account/" in url and "login" not in url):
                logger.success("Indeed logged in.")
                return True
            if "verify" in url or "challenge" in url or "2fa" in url:
                logger.warning("Indeed verification step - solve manually in browser")
            if self._check_captcha():
                logger.warning("Indeed hCaptcha challenge - attempting solver or manual fallback")
                self._wait_for_manual_captcha()
            time.sleep(2)

        raise LoginError("Indeed login timed out")

    def _check_captcha(self) -> bool:
        """Detect CAPTCHA presence."""
        if self.captcha_solver:
            try:
                from packages.stealth.captcha_solver import detect_captcha
                return detect_captcha(self.driver) is not None
            except Exception:
                pass
        try:
            self.driver.find_element(*SELECTORS["hcaptcha_iframe"])
            return True
        except NoSuchElementException:
            return False

    def _wait_for_manual_captcha(self, timeout=180):
        """
        Try auto-solve via solver, fallback to manual wait.
        """
        if self.captcha_solver and self.captcha_solver.enabled:
            try:
                from packages.stealth.captcha_solver import solve_if_present
                return solve_if_present(self.driver, self.captcha_solver)
            except Exception as e:
                logger.warning(f"CAPTCHA solver fallback to manual wait: {e}")

        logger.info(f"Waiting up to {timeout}s for manual hCaptcha solve...")
        end = time.time() + timeout
        while time.time() < end:
            if not self._check_captcha():
                logger.info("hCaptcha solved")
                human_sleep(2, 3)
                return True
            time.sleep(2)
        logger.warning("hCaptcha timeout - bot will attempt to continue")
        return False

    def search(self, filters: SearchFilters) -> None:
        """Navigate to Indeed search results page."""
        self.pause_current_run = False
        self.pause_reason = ""
        if not filters.queries:
            return False
        if self._last_search_time:
            elapsed = time.time() - self._last_search_time
            if elapsed < 15:
                sleep_for = 15 - elapsed
                logger.info(f"Indeed throttle: sleeping {sleep_for:.1f}s before next search")
                time.sleep(sleep_for)
        q = filters.queries[0]
        url = self._build_search_url(q, filters)
        logger.info(f"Indeed search: {q} -> {url}")
        self.driver.get(url)
        human_sleep(3, 5)
        self._last_search_time = time.time()
        if not handle_cloudflare_safely(self.driver, timeout=300, return_to_url=url):
            logger.warning("Cloudflare challenge could not be cleared for this search - pausing Indeed for this run")
            self.pause_current_run = True
            self.pause_reason = "Cloudflare challenge not cleared"
            try:
                self.driver.get(self.base_url)
                human_sleep(2, 4)
            except Exception:
                pass
            return False

        self._dismiss_search_overlay()
        return True

    def _dismiss_search_overlay(self) -> None:
        """
        Best-effort dismissal for onboarding or cookie overlays on Indeed search.

        This must never crash the whole run. Many overlays render hidden close
        buttons that are present in DOM but not interactable.
        """
        try:
            close_buttons = self.driver.find_elements(
                By.XPATH, "//button[@aria-label='close' or @aria-label='Close']"
            )
        except Exception:
            return

        for close_btn in close_buttons:
            try:
                if not close_btn.is_displayed():
                    continue
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    close_btn,
                )
                try:
                    close_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", close_btn)
                human_sleep(1, 2)
                return
            except Exception as e:
                logger.debug(f"Indeed overlay close skipped: {e}")

    def _build_search_url(self, query, f: SearchFilters) -> str:
        """Build Indeed search URL (Patch 31.1 fixed)."""
        return build_indeed_url_v2(self.base_url, query, f)

    def collect_job_cards(self, max_cards=50):
        """Collect cards using scoped selectors (Patch 31.1)."""
        state = detect_cloudflare_state(self.driver)
        if state["is_challenge"] and not handle_cloudflare_safely(
            self.driver,
            timeout=300,
            return_to_url=self.driver.current_url,
        ):
            logger.warning("Could not clear Cloudflare on Indeed results page - returning no cards")
            self.pause_current_run = True
            self.pause_reason = "Cloudflare challenge persisted on results page"
            return []
        return collect_indeed_cards_v2(
            driver=self.driver,
            max_cards=max_cards,
            scroll_count=self.config.get("scroll_count", 8),
            sleep_func=human_sleep,
            base_url=self.base_url,
        )

    @staticmethod
    def _safe_text(parent, selector):
        try:
            return parent.find_element(*selector).text.strip()
        except NoSuchElementException:
            return ""

    def open_job_detail(self, card):
        """Click card and extract detail."""
        d = self.driver
        el = card.get("_element")
        detail_url = card.get("url") or f"{self.base_url}/viewjob?jk={card['job_id']}"

        if el is None:
            el = self._refind_card_element(card["job_id"])
            if el is not None:
                card["_element"] = el

        if el is not None:
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.5)
            except StaleElementReferenceException:
                el = self._refind_card_element(card["job_id"])
                if el is not None:
                    card["_element"] = el
                    try:
                        d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.5)
                    except Exception:
                        pass

        click_target = el
        if el is not None:
            try:
                if (el.tag_name or "").lower() not in {"a", "button"}:
                    click_target = el.find_element(
                        By.CSS_SELECTOR,
                        "a[data-jk], h2.jobTitle a, a.jcs-JobTitle, a[href*='jk=']",
                    )
            except Exception:
                click_target = el

        clicked = False
        if click_target is not None:
            try:
                clicked = robust_click(d, click_target, max_retries=4, scroll=True)
            except Exception:
                clicked = False
        if not clicked:
            d.get(detail_url)

        human_sleep(2, 3.5)

        title = card.get("title") or (
            self._safe_text(el, SELECTORS["job_card_title"]) if el is not None else ""
        )
        if not title and el is not None:
            title = _extract_title_v2(el)
        detail_title = self._safe_text(d, SELECTORS["detail_title"])
        if detail_title:
            title = detail_title
        company = card.get("company") or self._safe_text(d, SELECTORS["detail_company"])
        location = card.get("location", "") or self._safe_text(d, SELECTORS["detail_location"])

        try:
            desc = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["detail_description"])).text
        except TimeoutException:
            desc = ""

        salary = self._safe_text(d, SELECTORS["detail_salary"])
        is_easy = self._detect_indeed_apply(d)

        return JobListing(
            platform=self.name,
            job_id=card["job_id"],
            title=title or f"Untitled indeed @ {company}" if company else "Untitled indeed",
            company=company,
            location=location,
            url=detail_url,
            description=desc,
            salary=salary,
            is_easy_apply=is_easy,
        )

    def _refind_card_element(self, job_id):
        selectors = [
            f"a[data-jk='{job_id}']",
            f"a[href*='jk={job_id}']",
            f"[data-jk='{job_id}']",
            f"[data-testid='slider_item'] a[href*='jk={job_id}']",
        ]
        for selector in selectors:
            try:
                return self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None

    def _detect_indeed_apply(self, driver) -> bool:
        """
        Multi-strategy detection of Indeed Apply (1-click) button.

        Returns True if "Apply on Indeed" button found (not external apply).
        """
        strategies = [
            ("indeed_apply_id", SELECTORS["indeed_apply_btn"]),
            ("apply_now_text", SELECTORS["apply_now_btn"]),
        ]

        for strategy_name, selector in strategies:
            try:
                elem = driver.find_element(*selector)
                if elem.is_displayed():
                    btn_text = (elem.text or "").lower()
                    aria = (elem.get_attribute("aria-label") or "").lower()

                    if any(kw in btn_text or kw in aria for kw in [
                        "company site", "company website", "external",
                        "site web", "auf der unternehmensseite",
                    ]):
                        logger.debug(f"Detected EXTERNAL apply via {strategy_name}: '{btn_text[:30]}'")
                        return False

                    logger.debug(f"Indeed Apply detected via: {strategy_name}")
                    return True
            except NoSuchElementException:
                continue

        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons[:50]:
                try:
                    text = (btn.text or "").lower()
                    aria = (btn.get_attribute("aria-label") or "").lower()
                    combined = f"{text} {aria}"

                    if "apply" in combined and btn.is_displayed():
                        if any(kw in combined for kw in ["company site", "external", "company website"]):
                            return False
                        logger.debug(f"Indeed Apply detected via text_scan: '{text[:30]}'")
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        self._last_detection_failure = "all_strategies_failed"
        return False

    def can_auto_apply(self, job):
        return bool(job.is_easy_apply)

    def apply(self, job, resume_path, mode="semi_auto", cover_letter_paths=None):
        """
        Apply to Indeed job using Indeed Apply (1-click) flow.

        Flow:
        1. Click "Apply now" button
        2. Indeed Apply iframe opens (modal)
        3. Switch to iframe
        4. Walk through steps (up to 10)
        5. Upload resume
        6. Answer screener questions
        7. Submit application
        8. Verify confirmation
        """
        d = self.driver
        qa_log, unanswered = [], []
        cover_letter_used = None

        if not job.is_easy_apply:
            return ApplicationResult(
                status=ApplyStatus.SKIPPED,
                skip_reason=SkipReason.NOT_EASY_APPLY,
                error_message="Indeed: Not an Indeed Apply job (external).",
            )

        btn = self._find_apply_button(d)
        if btn is None:
            return ApplicationResult(
                status=ApplyStatus.SKIPPED,
                skip_reason=SkipReason.NOT_EASY_APPLY,
                error_message="Apply button not found.",
            )

        try:
            btn.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            try:
                d.execute_script("arguments[0].click();", btn)
            except Exception as e:
                logger.warning(f"Apply click failed: {e}")
                return ApplicationResult(
                    status=ApplyStatus.SKIPPED,
                    error_message=f"Click failed: {e}",
                )

        human_sleep(3, 5)

        if not self._switch_to_ia_frame():
            return ApplicationResult(
                status=ApplyStatus.FAILED,
                error_message="Indeed Apply iframe not found.",
            )

        max_steps = 12
        previous_url = ""
        for step in range(max_steps):
            try:
                self.driver.switch_to.default_content()
                self._switch_to_ia_frame()
            except Exception:
                pass

            current_url = d.current_url
            logger.info(f"Indeed Apply step {step + 1}")

            if self._check_captcha():
                logger.warning("hCaptcha mid-apply - attempting solver or manual fallback")
                self._wait_for_manual_captcha()

            self._upload_resume_ia(resume_path)

            if cover_letter_paths:
                used = self._upload_cover_letter_ia(cover_letter_paths)
                if used:
                    cover_letter_used = used

            self._fill_text_inputs_ia(qa_log, unanswered, job)
            self._fill_selects_ia(qa_log, unanswered, job)
            self._fill_radios_ia(qa_log, unanswered, job)
            self._fill_checkboxes_ia(qa_log, unanswered, job)

            if current_url == previous_url and step > 2:
                logger.warning(f"Indeed Apply stuck at step {step+1}")
                self._screenshot_for_debug(job.job_id, f"stuck_step{step+1}")
                self.driver.switch_to.default_content()
                return ApplicationResult(
                    status=ApplyStatus.NEEDS_ANSWERS if unanswered else ApplyStatus.FAILED,
                    error_message=f"Stuck at step {step+1}",
                    qa_log=qa_log,
                    unanswered_questions=unanswered,
                )
            previous_url = current_url

            if self._click_button(SELECTORS["ia_submit_btn"]):
                human_sleep(3, 5)
                self.driver.switch_to.default_content()

                if self._verify_submitted():
                    return ApplicationResult(
                        status=ApplyStatus.APPLIED,
                        qa_log=qa_log,
                        unanswered_questions=unanswered,
                        resume_path=resume_path,
                        cover_letter_path=cover_letter_used,
                    )
                self._screenshot_for_debug(job.job_id, "verify_failed")
                return ApplicationResult(
                    status=ApplyStatus.FAILED,
                    error_message="Submit clicked but no confirmation.",
                    qa_log=qa_log,
                    unanswered_questions=unanswered,
                )

            if self._click_button(SELECTORS["ia_continue_btn"]):
                human_sleep(2, 4)
                if unanswered and mode == "semi_auto":
                    logger.warning(f"{len(unanswered)} unanswered Indeed questions")
                    self.driver.switch_to.default_content()
                    return ApplicationResult(
                        status=ApplyStatus.NEEDS_ANSWERS,
                        error_message="Unanswered Indeed question(s)",
                        qa_log=qa_log,
                        unanswered_questions=unanswered,
                    )
                continue

            logger.warning(f"No Continue/Submit button at step {step+1}")
            self._screenshot_for_debug(job.job_id, f"no_button_step{step+1}")
            break

        self.driver.switch_to.default_content()
        return ApplicationResult(
            status=ApplyStatus.FAILED,
            error_message="Max steps exceeded.",
            qa_log=qa_log,
            unanswered_questions=unanswered,
        )

    def _find_apply_button(self, driver, timeout=8):
        """Multi-strategy find of Indeed Apply button."""
        end = time.time() + timeout
        while time.time() < end:
            for selector in [SELECTORS["indeed_apply_btn"], SELECTORS["apply_now_btn"]]:
                try:
                    elem = driver.find_element(*selector)
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
                except NoSuchElementException:
                    continue
            time.sleep(0.5)
        return None

    def _switch_to_ia_frame(self) -> bool:
        """Switch driver context to Indeed Apply iframe."""
        end = time.time() + 8
        while time.time() < end:
            try:
                iframe = self.driver.find_element(*SELECTORS["ia_iframe"])
                self.driver.switch_to.frame(iframe)
                logger.debug("Switched to Indeed Apply iframe")
                return True
            except (NoSuchElementException, NoSuchFrameException):
                time.sleep(0.5)
        return False

    def _upload_resume_ia(self, resume_path):
        """Upload resume inside Indeed Apply iframe."""
        if not resume_path:
            return
        try:
            file_input = self.driver.find_element(*SELECTORS["ia_resume_upload"])
            abs_path = os.path.abspath(resume_path)
            if os.path.exists(abs_path):
                file_input.send_keys(abs_path)
                human_sleep(1, 2)
                logger.debug(f"Uploaded resume: {os.path.basename(abs_path)}")
        except NoSuchElementException:
            pass

    def _upload_cover_letter_ia(self, cover_letter_paths):
        """Upload cover letter if field exists."""
        if not cover_letter_paths:
            return None

        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for inp in inputs:
                name = (inp.get_attribute("name") or "").lower()
                if "cover" in name and cover_letter_paths.get("pdf"):
                    abs_path = os.path.abspath(cover_letter_paths["pdf"])
                    if os.path.exists(abs_path):
                        inp.send_keys(abs_path)
                        human_sleep(1, 2)
                        logger.info(f"Uploaded cover letter PDF: {os.path.basename(abs_path)}")
                        return cover_letter_paths["pdf"]
        except Exception:
            pass

        try:
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for ta in textareas:
                label = self._label_for(ta).lower()
                if "cover" in label and cover_letter_paths.get("txt"):
                    txt_path = cover_letter_paths["txt"]
                    if os.path.exists(txt_path):
                        with open(txt_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        ta.clear()
                        ta.send_keys(content)
                        logger.info("Filled cover letter textarea")
                        return txt_path
        except Exception:
            pass

        return None

    def _fill_text_inputs_ia(self, qa_log, unanswered, job):
        """Fill text/number/email inputs in iframe."""
        sels = "input[type='text'], input[type='tel'], input[type='number'], input[type='email'], textarea"
        for el in self.driver.find_elements(By.CSS_SELECTOR, sels):
            try:
                if el.get_attribute("value"):
                    continue
                label = self._label_for(el)
                val = self._lookup_answer(label, field_type="text")
                if val is None:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="text",
                        job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": None, "filled": False})
                    continue
                el.clear()
                type_human(el, str(val),
                           self.stealth_cfg["typing_min_delay"],
                           self.stealth_cfg["typing_max_delay"])
                qa_log.append({"q": label, "a": str(val), "filled": True})
            except StaleElementReferenceException:
                continue

    def _fill_selects_ia(self, qa_log, unanswered, job):
        """Fill select dropdowns in iframe."""
        for sel in self.driver.find_elements(By.TAG_NAME, "select"):
            try:
                label = self._label_for(sel)
                options = [o.text for o in Select(sel).options if o.text.strip()]
                val = self._lookup_answer(label, field_type="select", options=options)
                if val is None:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="select",
                        options=options, job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": None, "filled": False})
                    continue

                best = max(options,
                           key=lambda o: fuzz.partial_ratio(o.lower(), str(val).lower()),
                           default=None)
                if best:
                    Select(sel).select_by_visible_text(best)
                    qa_log.append({"q": label, "a": best, "filled": True})
            except Exception:
                continue

    def _fill_radios_ia(self, qa_log, unanswered, job):
        """Fill radio buttons in iframe."""
        seen = set()
        for r in self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
            try:
                name = r.get_attribute("name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)

                label = self._label_for_radio_group(name)
                options = self.driver.find_elements(By.CSS_SELECTOR, f"input[name='{name}']")
                option_labels = []
                for opt in options:
                    lbl_text = self._label_for(opt) or (opt.get_attribute("value") or "")
                    option_labels.append(lbl_text or "(no label)")

                val = self._lookup_answer(label, field_type="radio", options=option_labels)
                if val is None:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="radio",
                        options=option_labels, job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": None, "filled": False})
                    continue

                best_idx, best_score = None, 0
                val_lower = str(val).lower()
                for i, lbl in enumerate(option_labels):
                    if lbl and lbl != "(no label)":
                        s = fuzz.partial_ratio(lbl.lower(), val_lower)
                        if s > best_score:
                            best_idx, best_score = i, s

                if best_idx is not None and best_score >= 60:
                    try:
                        options[best_idx].click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", options[best_idx])
                    qa_log.append({"q": label, "a": option_labels[best_idx], "filled": True})
            except Exception as e:
                logger.debug(f"Radio fill error: {e}")

    def _fill_checkboxes_ia(self, qa_log, unanswered, job):
        """Auto-check consent checkboxes."""
        for cb in self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            try:
                if cb.is_selected():
                    continue
                label = self._label_for(cb).lower()
                if any(kw in label for kw in [
                    "terms", "privacy", "consent", "agree", "i confirm",
                    "i certify", "accept", "j'accepte", "akzeptieren",
                    "termini", "acepto",
                ]):
                    try:
                        cb.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", cb)
                    qa_log.append({"q": label, "a": "checked", "filled": True})
            except Exception:
                continue

    def _click_button(self, selector) -> bool:
        """Click button if present and enabled."""
        try:
            btns = self.driver.find_elements(*selector)
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        btn.click()
                        return True
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", btn)
                        return True
        except NoSuchElementException:
            return False
        return False

    def _verify_submitted(self) -> bool:
        """Verify application was submitted."""
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        end = time.time() + 12
        while time.time() < end:
            try:
                el = self.driver.find_element(*SELECTORS["submitted_indicator"])
                if el.is_displayed():
                    logger.info("Indeed Apply submit confirmed")
                    return True
            except NoSuchElementException:
                pass
            time.sleep(1)

        return False

    def _label_for(self, el):
        try:
            el_id = el.get_attribute("id")
            if el_id:
                lbls = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
                if lbls and lbls[0].text.strip():
                    return lbls[0].text.strip()
        except Exception:
            pass
        try:
            p = el.find_element(By.XPATH, "ancestor::label[1]")
            if p.text.strip():
                return p.text.strip()
        except NoSuchElementException:
            pass
        return (el.get_attribute("aria-label") or
                el.get_attribute("placeholder") or
                el.get_attribute("name") or "")

    def _label_for_radio_group(self, name):
        try:
            fs = self.driver.find_element(By.XPATH, f".//input[@name='{name}']/ancestor::fieldset[1]")
            try:
                legend = fs.find_element(By.TAG_NAME, "legend")
                if legend.text.strip():
                    return legend.text.strip()
            except NoSuchElementException:
                pass
        except NoSuchElementException:
            pass
        return name

    def _lookup_answer(self, question, field_type="text", options=None):
        """Find answer in profile, bank, or AI fallback."""
        if not question:
            return None
        q = question.strip().lower()

        for key, value in self.profile.as_field_map().items():
            if key in q and value:
                return value

        for k, v in self.answer_bank.items():
            if k.strip().lower() == q:
                return v

        for k, v in self.answer_bank.items():
            if k.strip().lower() in q or q in k.strip().lower():
                return v

        best_score, best_val = 0, None
        for k, v in self.answer_bank.items():
            s = fuzz.token_set_ratio(q, k.lower())
            if s > best_score:
                best_score, best_val = s, v
        if best_score >= 85:
            return best_val

        if (self.ai and _HAS_AI and self.ai.is_available()
                and self.ai_cfg.get("question_fallback", False)
                and self._candidate_facts):
            try:
                sys_prompt = self.ai_cfg.get("system_prompt") or None
                ai_answer = answer_question_with_ai(
                    self.ai, question, self._candidate_facts,
                    field_type=field_type, options=options,
                    system_prompt_template=sys_prompt,
                )
                if ai_answer:
                    if self.ai_cfg.get("auto_save_answers", True):
                        self._save_ai_answer(question, ai_answer)
                    return ai_answer
            except Exception as e:
                logger.warning(f"Indeed AI fallback error: {e}")

        return None

    def _save_ai_answer(self, question, answer):
        try:
            key = question.strip().lower()
            self.answer_bank[key] = answer
            if self._answers_file.exists():
                data = json.loads(self._answers_file.read_text(encoding="utf-8"))
            else:
                data = {}
            data[key] = answer
            self._answers_file.parent.mkdir(parents=True, exist_ok=True)
            self._answers_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Indeed saved AI answer: '{question[:50]}' -> '{answer}'")
        except Exception as e:
            logger.warning(f"Failed to save Indeed AI answer: {e}")

    def _screenshot_for_debug(self, job_id, tag):
        try:
            out_dir = Path("data/screenshots")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = out_dir / f"indeed_{tag}_{job_id}_{ts}.png"
            self.driver.save_screenshot(str(path))
            logger.info(f"Indeed screenshot: {path}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")
