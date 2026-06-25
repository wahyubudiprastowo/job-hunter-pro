"""
Robust click helpers for flaky Selenium job-card interactions.

Keeps the behavior additive: callers can still fall back to direct navigation
if all click strategies fail.
"""
from __future__ import annotations

import time

from loguru import logger
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains


def robust_click(driver, element, max_retries: int = 4, scroll: bool = True) -> bool:
    """
    Click an element using several fallback strategies.

    Returns True on first successful click attempt, otherwise False.
    """
    if element is None:
        return False

    if scroll:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
                element,
            )
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"robust_click scroll skipped: {e}")

    strategies = (
        ("action_chain", _click_via_action_chain),
        ("direct_click", _click_direct),
        ("js_click", _click_via_js),
        ("dispatch_event", _click_via_dispatch),
    )

    for strategy_name, strategy in strategies[: max(1, max_retries)]:
        try:
            if strategy(driver, element):
                return True
        except StaleElementReferenceException:
            logger.debug(f"robust_click stale element during {strategy_name}")
            return False
        except Exception as e:
            logger.debug(f"robust_click {strategy_name} failed: {e}")

    logger.debug("robust_click exhausted all strategies")
    return False


def _click_via_action_chain(driver, element) -> bool:
    try:
        ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
        return True
    except (ElementNotInteractableException, ElementClickInterceptedException):
        return False


def _click_direct(_driver, element) -> bool:
    try:
        element.click()
        return True
    except (ElementNotInteractableException, ElementClickInterceptedException):
        return False


def _click_via_js(driver, element) -> bool:
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        return False


def _click_via_dispatch(driver, element) -> bool:
    try:
        driver.execute_script(
            """
            var event = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true
            });
            arguments[0].dispatchEvent(event);
            """,
            element,
        )
        return True
    except Exception:
        return False
