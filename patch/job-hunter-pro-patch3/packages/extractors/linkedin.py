"""
LinkedIn extractor — PATCH 3 (AI question fallback).

Builds on PATCH 2 with:
- AI question fallback via packages.ai.question_bot
- Auto-save AI-resolved answers to data/answers.json
- AI ignored on cooldown / not available
- New constructor param: ai_provider (optional)
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

# Optional AI imports — extractor still works without
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


def _xpath_button_any(labels):
    conds = []
    for lbl in labels:
        conds.append(f"normalize-space(.)='{lbl}'")
        conds.append(f".//span[normalize-space(.)='{lbl}']")
        conds.append(f"contains(., '{lbl}')")
    return "//button[" + " or ".join(conds) + "]"


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
    "easy_apply_btn": (By.XPATH,
        "//button[contains(@class,'jobs-apply-button') and "
        "(contains(.,'Easy Apply') or contains(.,'Candidatura semplice') or "
        "contains(.,'Solicitud sencilla') or contains(.,'Candidature simplifiée') or "
        ".//span[contains(.,'Easy Apply')] or @aria-label[contains(.,'Easy Apply')])]"),
    "modal": (By.CSS_SELECTOR, ".jobs-easy-apply-modal, div[role='dialog']"),
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
                 ai_provider=None, ai_config=None):
        super().__init__(driver, config, profile, answer_bank, stealth_cfg)
        self.ai = ai_provider
        self.ai_cfg = ai_config or {}
        self._candidate_facts = None
        self._answers_file = Path("data/answers.json")
        if self.ai and _HAS_AI:
            try:
                self._candidate_facts = build_candidate_facts(profile, answer_bank)
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

    # ------------------------------------------------------------------
    def search(self, filters: SearchFilters) -> None:
        if not filters.queries:
            return
        q = filters.queries[0]
        url = self._build_search_url(q, filters)
        logger.info(f"🔎 LinkedIn search: {q} → {url}")
        self.driver.get(url)
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
        for _ in range(6):
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
        el = card["_element"]
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.5)
            ActionChains(d).move_to_element(el).pause(0.2).click().perform()
        except ElementClickInterceptedException:
            el.click()
        human_sleep(2, 3.5)
        title = card["title"] or self._safe_text(d, SELECTORS["detail_title"])
        company = card["company"] or self._safe_text(d, SELECTORS["detail_company"])
        try:
            desc = WebDriverWait(d, 10).until(
                EC.presence_of_element_located(SELECTORS["detail_description"])).text
        except TimeoutException:
            desc = ""
        salary = self._safe_text(d, SELECTORS["detail_salary"])
        is_easy = False
        try:
            d.find_element(*SELECTORS["easy_apply_btn"])
            is_easy = True
        except NoSuchElementException:
            pass
        return JobListing(
            platform=self.name, job_id=card["job_id"],
            title=title, company=company, location=card.get("location", ""),
            url=f"{self.base_url}/jobs/view/{card['job_id']}/",
            description=desc, salary=salary, is_easy_apply=is_easy,
        )

    def can_auto_apply(self, job):
        return bool(job.is_easy_apply)

    # ------------------------------------------------------------------
    # APPLY
    # ------------------------------------------------------------------
    def apply(self, job, resume_path, mode="semi_auto"):
        d = self.driver
        qa_log, unanswered = [], []

        if not job.is_easy_apply:
            return ApplicationResult(
                status=ApplyStatus.SKIPPED, skip_reason=SkipReason.NOT_EASY_APPLY,
                error_message="No Easy Apply button.")
        try:
            btn = WebDriverWait(d, 8).until(
                EC.element_to_be_clickable(SELECTORS["easy_apply_btn"]))
            btn.click()
        except TimeoutException:
            return ApplicationResult(
                status=ApplyStatus.SKIPPED, skip_reason=SkipReason.NOT_EASY_APPLY,
                error_message="Easy Apply not clickable.")
        human_sleep(2, 3.5)

        previous_progress = -1
        stuck_count = 0
        max_steps = 15

        for step in range(max_steps):
            try:
                modal = WebDriverWait(d, 8).until(
                    EC.presence_of_element_located(SELECTORS["modal"]))
            except TimeoutException:
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
            self._ensure_resume_selected(modal)

            if self._click_if_present(SELECTORS["btn_submit"]):
                if mode == "safe_auto":
                    logger.warning("⏸️  SAFE MODE — press ENTER.")
                    input(">>> ENTER: ")
                human_sleep(3, 5)
                if self._verify_submitted():
                    return ApplicationResult(
                        status=ApplyStatus.APPLIED, qa_log=qa_log,
                        unanswered_questions=unanswered, resume_path=resume_path)
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

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # FORM FILLERS
    # ------------------------------------------------------------------
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
                # Skip placeholder option (Seleziona / Selecionar / Option auswählen)
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

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # CORE: _lookup_answer with AI fallback
    # ------------------------------------------------------------------
    def _lookup_answer(self, question, field_type="text", options=None):
        """PATCH 3: now with AI fallback."""
        if not question:
            return None
        q = question.strip().lower()

        # Diversity auto-decline
        if any(kw in q for kw in DIVERSITY_KEYWORDS):
            return "Decline to self-identify"

        # 1) Personal info map
        for key, value in self.profile.as_field_map().items():
            if key in q and value:
                return value

        # 2) Answer bank exact
        for k, v in self.answer_bank.items():
            if k.strip().lower() == q:
                return v
        # 3) Substring
        for k, v in self.answer_bank.items():
            if k.strip().lower() in q or q in k.strip().lower():
                return v
        # 4) Full fuzzy
        best_score, best_val = 0, None
        for k, v in self.answer_bank.items():
            s = fuzz.token_set_ratio(q, k.lower())
            if s > best_score:
                best_score, best_val = s, v
        if best_score >= 85:
            return best_val

        # 5) === AI FALLBACK ===
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
                    # Auto-save for future reuse
                    if self.ai_cfg.get("auto_save_answers", True):
                        self._save_ai_answer(question, ai_answer)
                    return ai_answer
            except Exception as e:
                logger.warning(f"AI fallback error: {e}")

        return None

    def _save_ai_answer(self, question: str, answer: str):
        """Persist AI-resolved answer to data/answers.json for future reuse."""
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

    # ------------------------------------------------------------------
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
