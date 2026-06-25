"""
LinkedIn extractor — PATCH 13.

Fixes:
- Easy Apply detection now uses 5 strategies (was 1)
- Multi-language detection (German Sofortbewerbung, etc)
- Aria-label + class + text + icon-based detection
- Click fallback via JS if normal click fails
- Better diagnostic logging for skipped jobs
"""
from __future__ import annotations
import os
import time
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from loguru import logger
from rapidfuzz import fuzz

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
)

from packages.extractors.base import BaseExtractor
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


BTN_NEXT_LABELS = ["Next", "Continue", "Avanti", "Continua", "Siguiente", "Continuar",
                   "Suivant", "Continuer", "Weiter", "Próximo", "Próxima", "Volgende"]
BTN_REVIEW_LABELS = ["Review", "Rivedi", "Revisa", "Revoir", "Überprüfen", "Revisar", "Beoordelen"]
BTN_SUBMIT_LABELS = ["Submit application", "Submit", "Invia candidatura", "Invia",
                     "Enviar solicitud", "Enviar", "Envoyer la candidature", "Envoyer",
                     "Bewerbung absenden", "Absenden", "Verstuur sollicitatie", "Verstuur"]
BTN_DISCARD_LABELS = ["Discard", "Scarta", "Descartar", "Ignorer", "Verwerfen",
                      "Verwijderen", "Annulla", "Cancel"]

# PATCH 13: Multi-language Easy Apply button labels
EASY_APPLY_TEXTS = [
    "Easy Apply",              # English
    "Sofortbewerbung",          # German
    "Candidatura semplice",     # Italian
    "Solicitud sencilla",       # Spanish
    "Candidature simplifiée",   # French
    "Eenvoudig solliciteren",   # Dutch
    "Candidatura simples",      # Portuguese
    "Lätt ansökan",             # Swedish (just in case)
]


ALREADY_APPLIED_TEXTS = [
    "Applied",
    "Application submitted",
    "View application",
    "Candidatura inviata",
    "Candidatura presentata",
    "Visualizza candidatura",
    "Solicitud enviada",
    "Ver solicitud",
    "Candidature envoyée",
    "Voir la candidature",
    "Bewerbung gesendet",
    "Bewerbung anzeigen",
    "Sollicitatie verzonden",
    "Bekijk sollicitatie",
    "Candidatura enviada",
    "Ver candidatura",
]


def _xpath_button_any(labels):
    conds = []
    for lbl in labels:
        conds.append(f"normalize-space(.)='{lbl}'")
        conds.append(f".//span[normalize-space(.)='{lbl}']")
        conds.append(f"contains(., '{lbl}')")
    return "//button[" + " or ".join(conds) + "]"


# PATCH 13: Build comprehensive Easy Apply XPath
def _build_easy_apply_xpath():
    """Multi-strategy Easy Apply button detection."""
    parts = []
    # Strategy A: class-based
    parts.append("contains(@class,'jobs-apply-button')")
    parts.append("contains(@class,'jobs-apply')")
    # Strategy B: aria-label per language
    for txt in EASY_APPLY_TEXTS:
        parts.append(f"contains(@aria-label,'{txt}')")
    # Strategy C: text content
    for txt in EASY_APPLY_TEXTS:
        parts.append(f"contains(.,'{txt}')")
        parts.append(f".//span[contains(.,'{txt}')]")
    return "//button[" + " or ".join(parts) + "]"


SELECTORS = {
    "login_email": (By.ID, "username"),
    "login_password": (By.ID, "password"),
    "login_submit": (By.XPATH, "//button[@type='submit']"),
    "2fa_pin": (By.ID, "input__phone_verification_pin"),
    "results_list": (By.CSS_SELECTOR, ".scaffold-layout__list, .jobs-search-results-list"),
    "job_card": (By.CSS_SELECTOR, "div.job-card-container[data-job-id], li.jobs-search-results__list-item"),
    "job_card_title": (By.CSS_SELECTOR, "a.job-card-list__title, a.job-card-container__link"),
    "job_card_company": (By.CSS_SELECTOR, ".job-card-container__company-name, .artdeco-entity-lockup__subtitle"),
    "job_card_location": (By.CSS_SELECTOR, ".job-card-container__metadata-item, .artdeco-entity-lockup__caption"),
    "detail_title": (By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title"),
    "detail_company": (By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name a, .jobs-unified-top-card__company-name"),
    "detail_description": (By.CSS_SELECTOR, ".jobs-description__content, .jobs-description, .jobs-box__html-content"),
    "detail_salary": (By.CSS_SELECTOR, ".jobs-unified-top-card__salary-info, .salary-main-rail__salary"),
    # PATCH 13: New multi-strategy Easy Apply selector
    "easy_apply_btn": (By.XPATH, _build_easy_apply_xpath()),
    "modal": (By.CSS_SELECTOR,
        ".jobs-easy-apply-modal, "
        ".jobs-easy-apply-content, "
        ".artdeco-modal[role='dialog'], "
        "div[role='dialog']"),
    "btn_next": (By.XPATH, _xpath_button_any(BTN_NEXT_LABELS)),
    "btn_review": (By.XPATH, _xpath_button_any(BTN_REVIEW_LABELS)),
    "btn_submit": (By.XPATH, _xpath_button_any(BTN_SUBMIT_LABELS)),
    "btn_dismiss": (By.CSS_SELECTOR, "button[aria-label='Dismiss'], button[aria-label='Chiudi'], button[aria-label='Cerrar'], button[aria-label='Fermer']"),
    "save_dialog": (By.XPATH,
        "//*[contains(text(),'Save this application') or "
        "contains(text(),'Salva questa candidatura') or "
        "contains(text(),'Guardar esta solicitud') or "
        "contains(text(),'Sauvegarder cette candidature')]"),
    "save_dialog_discard": (By.XPATH,
        "//button[normalize-space(.)='Discard' or normalize-space(.)='Scarta' or "
        "normalize-space(.)='Descartar' or normalize-space(.)='Ignorer' or "
        "normalize-space(.)='Verwerfen']"),
    "modal_progress": (By.CSS_SELECTOR, "progress, [role='progressbar']"),
}

DATE_CODE = {"past_24h": "r86400", "past_week": "r604800", "past_month": "r2592000", "any": ""}
EXP_CODE = {"Internship": 1, "Entry level": 2, "Associate": 3, "Mid-Senior level": 4, "Director": 5, "Executive": 6}
JOB_TYPE_CODE = {"Full-time": "F", "Part-time": "P", "Contract": "C", "Temporary": "T", "Internship": "I", "Volunteer": "V"}

DIVERSITY_KEYWORDS = [
    "gender identity", "gender", "disability", "veteran", "race", "ethnicity",
    "ethnic", "sexual orientation", "transgender", "lgbtq", "pronoun",
    "self-identify", "self identify",
    "genere", "disabilità", "veterano", "etnia", "orientamento sessuale",
    "género", "discapacidad", "etnicidad",
    "genre", "handicap", "ethnique",
    "geschlecht", "behinderung",
]

DECLINE_OPTION_PATTERNS = [
    "prefer not", "decline", "don't wish", "do not wish", "not to say",
    "self-identify", "self identify", "rather not", "i don't want",
    "not specified",
    "preferisco non", "preferisco non rispondere", "non specificare",
    "prefiero no", "no especificar",
    "préfère ne pas", "ne souhaite pas",
    "möchte nicht", "keine angabe",
]


class LinkedInExtractor(BaseExtractor):
    name = "linkedin"
    base_url = "https://www.linkedin.com"
    requires_login = True
    supports_easy_apply = True

    def __init__(self, driver, config, profile, answer_bank, stealth_cfg,
                 ai_provider=None, ai_config=None, cv_text=None):
        super().__init__(driver, config, profile, answer_bank, stealth_cfg)
        self.ai = ai_provider
        self.ai_cfg = ai_config or {}
        self._candidate_facts = None
        self._cv_text = cv_text
        self._answers_file = Path("data/answers.json")
        self._last_detection_failure = None  # PATCH 13: diagnostic info
        if self.ai and _HAS_AI:
            try:
                self._candidate_facts = build_candidate_facts(profile, answer_bank, self._cv_text)
                logger.info("🧠 AI question fallback enabled.")
            except Exception as e:
                logger.warning(f"AI fact build failed: {e}")

    # ------------------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------------------
    def login(self, email, password, totp_secret=""):
        d = self.driver
        d.get(f"{self.base_url}/login")
        human_sleep(2, 3.5)
        if "feed" in d.current_url or "/in/" in d.current_url:
            logger.info("Already logged in.")
            return True
        if not email or not password:
            raise LoginError("LinkedIn credentials missing and no active session found")
        try:
            email_el = WebDriverWait(d, 15).until(
                EC.presence_of_element_located(SELECTORS["login_email"]))
            type_human(email_el, email, self.stealth_cfg["typing_min_delay"], self.stealth_cfg["typing_max_delay"])
            human_sleep(0.4, 1.0)
            pwd_el = d.find_element(*SELECTORS["login_password"])
            type_human(pwd_el, password, self.stealth_cfg["typing_min_delay"], self.stealth_cfg["typing_max_delay"])
            human_sleep(0.4, 1.0)
            d.find_element(*SELECTORS["login_submit"]).click()
        except TimeoutException:
            logger.warning("Login form not visible.")
        end = time.time() + 120
        while time.time() < end:
            url = d.current_url
            if "feed" in url or "/in/" in url or "/jobs" in url:
                logger.success("✅ Logged in.")
                return True
            if "checkpoint" in url or "challenge" in url or "two-step" in url:
                logger.warning("⚠️  2FA/CAPTCHA detected.")
                if totp_secret:
                    self._handle_2fa(totp_secret)
                else:
                    logger.warning("Solve manually in browser.")
            time.sleep(2)
        raise LoginError("Login timed out.")

    def _handle_2fa(self, totp_secret):
        try:
            import pyotp
            code = pyotp.TOTP(totp_secret).now()
            inp = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(SELECTORS["2fa_pin"]))
            type_human(inp, code)
            self.driver.find_element(By.ID, "two-step-submit-button").click()
            human_sleep(2, 4)
        except Exception as e:
            logger.error(f"2FA failed: {e}")

    def search(self, filters: SearchFilters) -> None:
        if not filters.queries:
            return
        q = filters.queries[0]
        url = self._build_search_url(q, filters)
        logger.info(f"🔎 LinkedIn search: {q} → {url}")
        last_error = None
        for attempt in range(2):
            try:
                self.driver.get(url)
                last_error = None
                break
            except TimeoutException as e:
                last_error = e
                logger.warning(
                    f"LinkedIn search timeout on attempt {attempt + 1}/2 for '{q}': {e}"
                )
                try:
                    self.driver.execute_script("window.stop();")
                except Exception:
                    pass
                try:
                    current_url = (self.driver.current_url or "").lower()
                except Exception:
                    current_url = ""
                if "/jobs" in current_url:
                    logger.info("LinkedIn jobs page partially loaded after timeout - continuing.")
                    last_error = None
                    break
                if attempt == 0:
                    try:
                        self.driver.get(f"{self.base_url}/jobs/")
                        human_sleep(2, 3)
                    except Exception:
                        pass
                    continue
                raise
        human_sleep(3, 5)

    def _build_search_url(self, query, f):
        parts = [f"keywords={quote(query)}", f"location={quote(f.location)}"]
        if f.easy_apply_only:
            parts.append("f_AL=true")
        if f.remote:
            parts.append("f_WT=2")
        if f.hybrid:
            parts.append("f_WT=3")
        if f.date_posted in DATE_CODE and DATE_CODE[f.date_posted]:
            parts.append(f"f_TPR={DATE_CODE[f.date_posted]}")
        for lvl in f.experience_levels:
            if lvl in EXP_CODE:
                parts.append(f"f_E={EXP_CODE[lvl]}")
        if f.job_type in JOB_TYPE_CODE:
            parts.append(f"f_JT={JOB_TYPE_CODE[f.job_type]}")
        return f"{self.base_url}/jobs/search/?" + "&".join(parts)

    def collect_job_cards(self, max_cards=50):
        d = self.driver
        cards, seen = [], set()
        # PATCH 13: Increased scrolls from 6 to 12 for more cards
        scroll_count = self.config.get("scroll_count", 12) if self.config else 12
        for _ in range(scroll_count):
            try:
                ul = WebDriverWait(d, 10).until(
                    EC.presence_of_element_located(SELECTORS["results_list"]))
                d.execute_script("arguments[0].scrollBy(0, 800);", ul)
            except TimeoutException:
                d.execute_script("window.scrollBy(0, 800);")
            human_sleep(1.2, 2.2)
        nodes = d.find_elements(*SELECTORS["job_card"])
        logger.info(f"Found {len(nodes)} job card nodes.")
        for node in nodes[:max_cards]:
            try:
                jid = node.get_attribute("data-job-id") or node.get_attribute("data-occludable-job-id")
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                cards.append({
                    "job_id": jid,
                    "title": self._safe_text(node, SELECTORS["job_card_title"]),
                    "company": self._safe_text(node, SELECTORS["job_card_company"]),
                    "location": self._safe_text(node, SELECTORS["job_card_location"]),
                    "_element": node,
                })
            except StaleElementReferenceException:
                continue
        logger.info(f"📋 Collected {len(cards)} unique cards.")
        return cards

    @staticmethod
    def _safe_text(parent, selector):
        try:
            return parent.find_element(*selector).text.strip()
        except NoSuchElementException:
            return ""

    def open_job_detail(self, card):
        d = self.driver
        el = card.get("_element")
        if el is None:
            target_url = card.get("url") or f"{self.base_url}/jobs/view/{card['job_id']}/"
            d.get(target_url)
            human_sleep(2, 3.5)
            title = card.get("title") or self._safe_text(d, SELECTORS["detail_title"])
            company = card.get("company") or self._safe_text(d, SELECTORS["detail_company"])
            try:
                desc = WebDriverWait(d, 10).until(
                    EC.presence_of_element_located(SELECTORS["detail_description"])).text
            except TimeoutException:
                desc = ""
            salary = self._safe_text(d, SELECTORS["detail_salary"])
            already_applied = self._detect_already_applied(d)
            is_easy = False
            if not already_applied:
                is_easy = self._detect_easy_apply(d)
                if not is_easy:
                    is_easy = self._find_easy_apply_button(d, timeout=2) is not None
            return JobListing(
                platform=self.name, job_id=card["job_id"],
                title=title, company=company, location=card.get("location", ""),
                url=target_url,
                description=desc, salary=salary, is_easy_apply=is_easy,
                raw={"already_applied": already_applied},
            )
        # PATCH 13: Stale-element-safe scroll
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.5)
        except StaleElementReferenceException:
            # Re-find card by job_id
            logger.debug(f"Stale element, re-finding card {card['job_id']}")
            try:
                el = d.find_element(
                    By.CSS_SELECTOR,
                    f"[data-occludable-job-id='{card['job_id']}'], "
                    f"[data-job-id='{card['job_id']}']"
                )
                card["_element"] = el
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.5)
            except Exception:
                pass
        try:
            ActionChains(d).move_to_element(el).pause(0.2).click().perform()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            try:
                el.click()
            except Exception:
                d.execute_script("arguments[0].click();", el)
        human_sleep(2, 3.5)
        title = card["title"] or self._safe_text(d, SELECTORS["detail_title"])
        company = card["company"] or self._safe_text(d, SELECTORS["detail_company"])
        try:
            desc = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["detail_description"])).text
        except TimeoutException:
            desc = ""
        salary = self._safe_text(d, SELECTORS["detail_salary"])
        already_applied = self._detect_already_applied(d, card)

        # PATCH 13: Multi-strategy Easy Apply detection with click-finder fallback
        is_easy = False
        if not already_applied:
            is_easy = self._detect_easy_apply(d)
            if not is_easy:
                is_easy = self._find_easy_apply_button(d, timeout=2) is not None

        return JobListing(
            platform=self.name, job_id=card["job_id"],
            title=title, company=company, location=card.get("location", ""),
            url=f"{self.base_url}/jobs/view/{card['job_id']}/",
            description=desc, salary=salary, is_easy_apply=is_easy,
            raw={"already_applied": already_applied},
        )

    def _detect_already_applied(self, driver, card=None) -> bool:
        """Detect already-applied state only within the active card/detail scope."""
        scoped_roots = []

        if card and card.get("_element") is not None:
            scoped_roots.append(card["_element"])

        detail_scope_selectors = [
            (By.CSS_SELECTOR, ".jobs-search__job-details--container"),
            (By.CSS_SELECTOR, ".scaffold-layout__detail"),
            (By.CSS_SELECTOR, ".jobs-details"),
            (By.TAG_NAME, "main"),
        ]
        for by, sel in detail_scope_selectors:
            try:
                scoped_roots.append(driver.find_element(by, sel))
                break
            except NoSuchElementException:
                continue
            except Exception:
                continue

        scoped_xpath_checks = [
            ".//button[contains(.,'View application')]",
            ".//button[contains(.,'Application submitted')]",
            ".//*[contains(@class,'jobs-s-apply') and contains(.,'Applied')]",
            ".//*[contains(@class,'jobs-apply-button') and contains(.,'Applied')]",
            ".//*[contains(.,'Applied') and contains(.,'ago')]",
        ]

        for root in scoped_roots:
            for sel in scoped_xpath_checks:
                try:
                    elem = root.find_element(By.XPATH, sel)
                    if elem.is_displayed():
                        logger.info("ðŸ” LinkedIn indicates this job was already applied.")
                        return True
                except NoSuchElementException:
                    continue
                except Exception:
                    continue

        for root in scoped_roots:
            try:
                scoped_text = (root.text or "").lower()
                for marker in ALREADY_APPLIED_TEXTS:
                    if marker.lower() in scoped_text:
                        logger.info(f"ðŸ” Already-applied marker detected in scoped view: {marker}")
                        return True
            except Exception:
                continue

        return False

    def _detect_easy_apply(self, driver) -> bool:
        """
        PATCH 13: Multi-strategy Easy Apply detection.
        Returns True if button found via ANY of 5 strategies.
        """
        strategies = [
            ("main_selector", SELECTORS["easy_apply_btn"]),
            ("apply_button_class", (By.CSS_SELECTOR,
                "button.jobs-apply-button, button.jobs-apply, "
                "button[data-test-button-action='apply']")),
            ("aria_label_lower", (By.XPATH,
                "//button[@aria-label[contains(translate(.,'EASY APPLY','easy apply'),'easy apply')]]")),
            ("icon_button", (By.XPATH,
                "//button[.//svg[contains(@class,'jobs-apply-icon')] or "
                ".//svg[@aria-label[contains(.,'Easy Apply')]]]")),
        ]
        
        for strategy_name, selector in strategies:
            try:
                elem = driver.find_element(*selector)
                if elem.is_displayed():
                    logger.debug(f"✅ Easy Apply detected via: {strategy_name}")
                    self._last_detection_failure = None
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                continue
        
        # Strategy 5: Last resort — text search across all buttons
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                try:
                    text = (btn.text or "").lower()
                    aria = (btn.get_attribute("aria-label") or "").lower()
                    combined = f"{text} {aria}"
                    for kw in [
                        "easy apply", "sofortbewerbung",
                        "candidatura semplice", "solicitud sencilla",
                        "candidature simplifiée", "eenvoudig solliciteren",
                        "candidatura simples",
                    ]:
                        if kw in combined and btn.is_displayed():
                            logger.debug(f"✅ Easy Apply detected via: text_search ({kw})")
                            self._last_detection_failure = None
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        
        # All strategies failed
        try:
            page_url = driver.current_url
            self._last_detection_failure = f"all_strategies_failed at {page_url[:60]}"
        except Exception:
            self._last_detection_failure = "all_strategies_failed"
        logger.debug(f"❌ Easy Apply NOT detected: {self._last_detection_failure}")
        return False

    def _find_easy_apply_button(self, driver, timeout: int = 8):
        """PATCH 13: Find Easy Apply button (for clicking) using multi-strategy."""
        end = time.time() + timeout
        strategies = [
            SELECTORS["easy_apply_btn"],
            (By.CSS_SELECTOR, "button.jobs-apply-button, button.jobs-apply"),
            (By.CSS_SELECTOR, "button[data-live-test-job-apply-button], button[data-test-button-action='apply']"),
            (By.XPATH, "//button[@aria-label[contains(translate(.,'EASY APPLY','easy apply'),'easy apply')]]"),
        ]
        while time.time() < end:
            for selector in strategies:
                try:
                    elem = driver.find_element(*selector)
                    if elem.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                        except Exception:
                            pass
                        if elem.is_enabled():
                            return elem
                except NoSuchElementException:
                    continue
                except Exception:
                    continue

            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for elem in buttons:
                    try:
                        text = (elem.text or "").strip().lower()
                        aria = (elem.get_attribute("aria-label") or "").strip().lower()
                        klass = (elem.get_attribute("class") or "").strip().lower()
                        combined = f"{text} {aria} {klass}"
                        if "easy apply" in combined and elem.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                            except Exception:
                                pass
                            if elem.is_enabled():
                                return elem
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def can_auto_apply(self, job):
        return bool(job.is_easy_apply)

    # ------------------------------------------------------------------
    # APPLY (rest unchanged from your current version)
    # ------------------------------------------------------------------
    def apply(self, job, resume_path, mode="semi_auto", cover_letter_paths=None):
        d = self.driver
        qa_log, unanswered = [], []
        uploaded_cover_letter_path = None

        if not job.is_easy_apply:
            return ApplicationResult(
                status=ApplyStatus.SKIPPED, skip_reason=SkipReason.NOT_EASY_APPLY,
                error_message="No Easy Apply button.")
        
        # PATCH 13: Multi-strategy button find + JS fallback click
        btn = self._find_easy_apply_button(d, timeout=12)
        if btn is None:
            return ApplicationResult(
                status=ApplyStatus.FAILED,
                error_message="Easy Apply detected earlier but button was not clickable.")
        try:
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception:
                pass
            btn.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            try:
                ActionChains(d).move_to_element(btn).pause(0.2).click().perform()
            except Exception as e:
                try:
                    d.execute_script("arguments[0].click();", btn)
                except Exception:
                    logger.warning(f"Easy Apply click failed: {e}")
                    return ApplicationResult(
                        status=ApplyStatus.FAILED,
                        error_message=f"Easy Apply click failed: {e}")
        
        human_sleep(2, 3.5)

        previous_progress = -1
        stuck_count = 0
        max_steps = 15

        for step in range(max_steps):
            modal = self._wait_for_apply_modal(btn if step == 0 else None, timeout=12)
            if modal is None:
                return ApplicationResult(
                    status=ApplyStatus.FAILED, error_message="Modal not found.",
                    qa_log=qa_log, unanswered_questions=unanswered)
            human_sleep(0.8, 1.6)

            progress = self._read_progress()
            logger.info(f"📋 Step {step+1} — Easy Apply progress: {progress}%")

            if progress == previous_progress:
                stuck_count += 1
            else:
                stuck_count = 0
            previous_progress = progress

            if stuck_count >= 2:
                logger.warning(f"🚧 Stuck at {progress}% — aborting.")
                self._screenshot_for_debug(job.job_id, f"stuck_{progress}pct")
                self._close_and_discard()
                return ApplicationResult(
                    status=ApplyStatus.NEEDS_ANSWERS if unanswered else ApplyStatus.FAILED,
                    error_message=f"Stuck at {progress}%.",
                    qa_log=qa_log, unanswered_questions=unanswered)

            self._fill_text_inputs(modal, qa_log, unanswered, job)
            self._fill_selects(modal, qa_log, unanswered, job)
            self._fill_radios(modal, qa_log, unanswered, job)
            self._fill_checkboxes(modal, qa_log, unanswered, job)
            self._upload_resume(modal, resume_path)
            uploaded_cover_letter_path = (
                uploaded_cover_letter_path
                or self._upload_cover_letter(modal, cover_letter_paths)
            )
            self._ensure_resume_selected(modal)

            if self._click_if_present(SELECTORS["btn_submit"]):
                if mode == "safe_auto":
                    logger.warning("⏸️  SAFE MODE — press ENTER.")
                    input(">>> ENTER: ")
                human_sleep(3, 5)
                if self._verify_submitted():
                    return ApplicationResult(
                        status=ApplyStatus.APPLIED, qa_log=qa_log,
                        unanswered_questions=unanswered, resume_path=resume_path,
                        cover_letter_path=uploaded_cover_letter_path)
                else:
                    self._screenshot_for_debug(job.job_id, "verify_failed")
                    return ApplicationResult(
                        status=ApplyStatus.FAILED,
                        error_message="Submit clicked but no confirmation.",
                        qa_log=qa_log, unanswered_questions=unanswered)

            if self._click_if_present(SELECTORS["btn_review"]):
                human_sleep(1.5, 2.5)
                continue

            if self._click_if_present(SELECTORS["btn_next"]):
                human_sleep(1.5, 2.5)
                if unanswered and mode == "semi_auto":
                    logger.warning(f"❓ {len(unanswered)} unanswered. Closing.")
                    self._close_and_discard()
                    return ApplicationResult(
                        status=ApplyStatus.NEEDS_ANSWERS,
                        error_message="Unanswered question(s).",
                        qa_log=qa_log, unanswered_questions=unanswered)
                continue

            logger.warning("No Next/Review/Submit button.")
            self._screenshot_for_debug(job.job_id, "no_button")
            self._close_and_discard()
            return ApplicationResult(
                status=ApplyStatus.FAILED,
                error_message="No navigation button.",
                qa_log=qa_log, unanswered_questions=unanswered)

        self._close_and_discard()
        return ApplicationResult(
            status=ApplyStatus.FAILED, error_message="Max steps exceeded.",
            qa_log=qa_log, unanswered_questions=unanswered)

    def _upload_cover_letter(self, modal, cover_letter_paths):
        if not cover_letter_paths:
            return None

        txt_path = cover_letter_paths.get("txt")
        pdf_path = cover_letter_paths.get("pdf")
        field = self._find_cover_letter_field(modal)
        if not field:
            return None

        field_type, element = field

        try:
            if field_type == "file" and pdf_path:
                abs_path = os.path.abspath(pdf_path)
                if os.path.exists(abs_path):
                    element.send_keys(abs_path)
                    human_sleep(1, 2)
                    logger.info(f"💌 Uploaded cover letter PDF: {pdf_path}")
                    return pdf_path

            if field_type == "textarea" and txt_path:
                abs_txt = os.path.abspath(txt_path)
                if os.path.exists(abs_txt):
                    text = Path(abs_txt).read_text(encoding="utf-8").strip()
                    if text and not element.get_attribute("value"):
                        element.clear()
                        type_human(
                            element,
                            text,
                            self.stealth_cfg["typing_min_delay"],
                            self.stealth_cfg["typing_max_delay"],
                        )
                        logger.info(f"💌 Filled cover letter textarea: {txt_path}")
                        return txt_path
        except StaleElementReferenceException:
            return None
        except Exception as e:
            logger.warning(f"Cover letter upload skipped: {e}")
            return None

        return None

    def _wait_for_apply_modal(self, trigger_btn=None, timeout: int = 12):
        end = time.time() + timeout
        retried_click = False

        while time.time() < end:
            try:
                candidates = self.driver.find_elements(*SELECTORS["modal"])
                for candidate in candidates:
                    try:
                        if candidate.is_displayed():
                            return candidate
                    except StaleElementReferenceException:
                        continue
            except Exception:
                pass

            if trigger_btn is not None and not retried_click and time.time() + 3 < end:
                try:
                    self.driver.execute_script("arguments[0].click();", trigger_btn)
                    retried_click = True
                    human_sleep(1, 1.8)
                    continue
                except Exception:
                    retried_click = True

            time.sleep(0.5)

        return None

    def _find_cover_letter_field(self, modal):
        keywords = [
            "cover", "cover letter",
            "lettera", "presentazione",
            "anschreiben",
            "carta de presentación",
            "lettre de motivation",
        ]

        file_selectors = [
            "input[type='file'][name*='cover' i]",
            "input[type='file'][id*='cover' i]",
            "input[type='file'][name*='letter' i]",
            "input[type='file'][id*='letter' i]",
        ]
        for selector in file_selectors:
            try:
                elem = modal.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    return ("file", elem)
            except NoSuchElementException:
                continue

        textarea_selectors = [
            "textarea[id*='cover' i]",
            "textarea[name*='cover' i]",
            "textarea[id*='letter' i]",
            "textarea[name*='letter' i]",
        ]
        for selector in textarea_selectors:
            try:
                elem = modal.find_element(By.CSS_SELECTOR, selector)
                if elem.is_displayed():
                    return ("textarea", elem)
            except NoSuchElementException:
                continue

        try:
            textareas = modal.find_elements(By.TAG_NAME, "textarea")
        except Exception:
            textareas = []

        for elem in textareas:
            try:
                label = self._label_for(elem).lower()
                if any(keyword in label for keyword in keywords):
                    return ("textarea", elem)
            except Exception:
                continue

        try:
            file_inputs = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
        except Exception:
            file_inputs = []

        for elem in file_inputs:
            try:
                label = self._label_for(elem).lower()
                if any(keyword in label for keyword in keywords):
                    return ("file", elem)
            except Exception:
                continue

        return None

    def _read_progress(self) -> int:
        try:
            el = self.driver.find_element(*SELECTORS["modal_progress"])
            val = el.get_attribute("value") or el.get_attribute("aria-valuenow") or "0"
            return int(float(val))
        except (NoSuchElementException, ValueError):
            return -1

    def _ensure_resume_selected(self, modal):
        try:
            radios = modal.find_elements(
                By.CSS_SELECTOR,
                "input[type='radio'][name*='resume'], "
                "input[type='radio'][name*='curriculum'], "
                "input[type='radio'][name*='cv'], "
                ".jobs-document-upload-redesign-card__container input[type='radio']"
            )
            if not radios:
                return
            if any(r.is_selected() for r in radios):
                return
            try:
                radios[0].click()
                logger.info("📄 Auto-selected first resume.")
                human_sleep(0.5, 1.0)
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", radios[0])
        except Exception as e:
            logger.debug(f"Resume auto-select skipped: {e}")

    def _close_and_discard(self):
        try:
            self.driver.find_element(*SELECTORS["btn_dismiss"]).click()
            human_sleep(0.8, 1.5)
        except NoSuchElementException:
            pass
        end = time.time() + 3
        while time.time() < end:
            try:
                self.driver.find_element(*SELECTORS["save_dialog"])
                try:
                    btn = self.driver.find_element(*SELECTORS["save_dialog_discard"])
                    btn.click()
                except NoSuchElementException:
                    try:
                        btn = self.driver.find_element(By.XPATH, _xpath_button_any(BTN_DISCARD_LABELS))
                        btn.click()
                    except NoSuchElementException:
                        pass
                logger.info("🗑️  Discarded draft.")
                human_sleep(0.5, 1.2)
                return
            except NoSuchElementException:
                time.sleep(0.3)

    def _fill_text_inputs(self, modal, qa_log, unanswered, job):
        sels = "input[type='text'], input[type='tel'], input[type='number'], input[type='email'], textarea"
        for el in modal.find_elements(By.CSS_SELECTOR, sels):
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

    def _fill_selects(self, modal, qa_log, unanswered, job):
        for sel in modal.find_elements(By.TAG_NAME, "select"):
            try:
                label = self._label_for(sel)
                options = [o.text for o in Select(sel).options if o.text.strip()]
                placeholders = ("Seleziona", "Selecionar", "auswählen", "Sélectionner", "Select")
                real_options = [o for o in options
                                if not any(o.startswith(p) for p in placeholders)]
                val = self._lookup_answer(label, field_type="select", options=real_options)
                if val is None:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="select",
                        options=options, job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": None, "filled": False, "options": options})
                    continue
                if any(p in str(val).lower() for p in ["decline", "prefer not"]):
                    for o in options:
                        if any(p in o.lower() for p in DECLINE_OPTION_PATTERNS):
                            Select(sel).select_by_visible_text(o)
                            qa_log.append({"q": label, "a": o, "filled": True})
                            break
                    continue
                best = max(options,
                           key=lambda o: fuzz.partial_ratio(o.lower(), str(val).lower()),
                           default=None)
                if best:
                    Select(sel).select_by_visible_text(best)
                    qa_log.append({"q": label, "a": best, "filled": True})
            except Exception:
                continue

    def _fill_radios(self, modal, qa_log, unanswered, job):
        seen = set()
        for r in modal.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
            try:
                name = r.get_attribute("name") or ""
                if not name or name in seen:
                    continue
                if any(kw in name.lower() for kw in ["resume", "curriculum", "cv"]):
                    seen.add(name)
                    continue
                seen.add(name)
                label = self._label_for_radio_group(modal, name)
                options = modal.find_elements(By.CSS_SELECTOR, f"input[name='{name}']")
                option_labels = []
                for opt in options:
                    lbl_text = ""
                    opt_id = opt.get_attribute("id") or ""
                    if opt_id:
                        try:
                            lbl = modal.find_element(By.CSS_SELECTOR, f"label[for='{opt_id}']")
                            lbl_text = lbl.text.strip()
                        except NoSuchElementException:
                            pass
                    if not lbl_text:
                        try:
                            lbl = opt.find_element(By.XPATH, "ancestor::label[1]")
                            lbl_text = lbl.text.strip()
                        except NoSuchElementException:
                            pass
                    if not lbl_text:
                        lbl_text = (opt.get_attribute("aria-label") or "").strip()
                    if not lbl_text:
                        v = (opt.get_attribute("value") or "").strip()
                        if v and not v.replace("_", "").replace("-", "").isdigit():
                            lbl_text = v
                    option_labels.append(lbl_text or "(no label)")

                val = self._lookup_answer(label, field_type="radio", options=option_labels)
                if val is None:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="radio",
                        options=option_labels, job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": None, "filled": False, "options": option_labels})
                    continue

                best_idx, best_score = None, 0
                val_lower = str(val).lower()
                wants_decline = any(p in val_lower for p in ["decline", "prefer not", "self-identify"])
                if wants_decline:
                    for i, lbl in enumerate(option_labels):
                        if any(p in lbl.lower() for p in DECLINE_OPTION_PATTERNS):
                            best_idx, best_score = i, 100
                            break
                if best_idx is None:
                    for i, lbl in enumerate(option_labels):
                        if not lbl or lbl == "(no label)":
                            continue
                        s = fuzz.partial_ratio(lbl.lower(), val_lower)
                        if s > best_score:
                            best_idx, best_score = i, s

                if best_idx is not None and best_score >= 60:
                    try:
                        options[best_idx].click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", options[best_idx])
                    qa_log.append({"q": label, "a": option_labels[best_idx], "filled": True})
                else:
                    unanswered.append(UnansweredQuestion(
                        question=label or "(unknown)", field_type="radio",
                        options=option_labels, job_id=job.job_id, platform=self.name))
                    qa_log.append({"q": label, "a": val, "filled": False, "options": option_labels})
            except Exception as e:
                logger.debug(f"Radio fill error: {e}")
                continue

    def _fill_checkboxes(self, modal, qa_log, unanswered, job):
        for cb in modal.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            try:
                if cb.is_selected():
                    continue
                label = self._label_for(cb).lower()
                if any(kw in label for kw in
                       ["terms", "privacy", "consent", "agree", "acknowledge",
                        "i confirm", "i certify", "termini", "consenso", "accetto",
                        "términos", "acepto", "conditions", "j'accepte",
                        "bedingungen", "ich stimme zu"]):
                    try:
                        cb.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", cb)
                    qa_log.append({"q": label, "a": "checked", "filled": True})
            except Exception:
                continue

    def _upload_resume(self, modal, resume_path):
        if not resume_path:
            return
        try:
            file_input = modal.find_element(By.CSS_SELECTOR, "input[type='file']")
            abs_path = os.path.abspath(resume_path)
            if os.path.exists(abs_path):
                file_input.send_keys(abs_path)
                human_sleep(1, 2)
        except NoSuchElementException:
            pass

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
            t = p.text.strip()
            if t:
                return t
        except NoSuchElementException:
            pass
        return (el.get_attribute("aria-label") or
                el.get_attribute("placeholder") or
                el.get_attribute("name") or "")

    def _label_for_radio_group(self, modal, name):
        try:
            legend = modal.find_element(
                By.XPATH, f".//input[@name='{name}']/ancestor::fieldset//legend")
            return legend.text.strip()
        except NoSuchElementException:
            pass
        try:
            fs = modal.find_element(By.XPATH, f".//input[@name='{name}']/ancestor::fieldset[1]")
            for tag in ("legend", "label", "span"):
                try:
                    el = fs.find_element(By.TAG_NAME, tag)
                    if el.text.strip():
                        return el.text.strip()
                except NoSuchElementException:
                    continue
        except NoSuchElementException:
            pass
        return name

    def _lookup_answer(self, question, field_type="text", options=None):
        if not question:
            return None
        q = question.strip().lower()
        if any(kw in q for kw in DIVERSITY_KEYWORDS):
            return "Decline to self-identify"
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
                logger.warning(f"AI fallback error: {e}")
        return None

    def _save_ai_answer(self, question: str, answer: str):
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
            logger.info(f"💾 Saved AI answer: '{question[:50]}' -> '{answer}'")
        except Exception as e:
            logger.warning(f"Failed to save AI answer: {e}")

    def _click_if_present(self, selector):
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

    def _verify_submitted(self):
        indicators = [
            (By.XPATH, "//h2[contains(.,'Application sent') or contains(.,'application was sent') or contains(.,'Candidatura inviata') or contains(.,'Solicitud enviada') or contains(.,'Candidature envoyée') or contains(.,'Bewerbung gesendet')]"),
            (By.XPATH, "//h3[contains(.,'Application sent') or contains(.,'Candidatura inviata')]"),
            (By.XPATH, "//*[contains(text(),'Your application was sent') or contains(text(),'La tua candidatura è stata inviata')]"),
            (By.XPATH, "//*[contains(text(),'Application submitted') or contains(text(),'Done') or contains(text(),'Fatto')]"),
            (By.CSS_SELECTOR, ".artdeco-inline-feedback--success"),
            (By.CSS_SELECTOR, ".jobs-easy-apply-content__success-message"),
            (By.CSS_SELECTOR, ".jobs-post-apply-modal"),
        ]
        end = time.time() + 12
        while time.time() < end:
            for by, sel in indicators:
                try:
                    el = self.driver.find_element(by, sel)
                    if el.is_displayed():
                        logger.info(f"✅ Submit confirmed.")
                        self._close_and_discard()
                        return True
                except NoSuchElementException:
                    continue
            try:
                self.driver.find_element(*SELECTORS["modal"])
            except NoSuchElementException:
                logger.info("✅ Submit confirmed (modal closed).")
                return True
            time.sleep(0.5)
        return False

    def _screenshot_for_debug(self, job_id, tag):
        try:
            out_dir = Path("data/screenshots")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = out_dir / f"{tag}_{job_id}_{ts}.png"
            self.driver.save_screenshot(str(path))
            logger.info(f"📸 Screenshot: {path}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")
