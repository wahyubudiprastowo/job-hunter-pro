"""
Robust Click Utility (Patch 33.3).

Solves common Selenium issues:
- "element not interactable" (no size/location)
- "element click intercepted"
- Stale element references

Strategy:
1. Scroll element into center view
2. Wait for visibility
3. Try ActionChains click
4. Fallback to JavaScript click
5. Last resort: dispatch event
"""
from __future__ import annotations
import time
from typing import Optional
from loguru import logger

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)


def robust_click(driver, element, max_retries: int = 3, scroll: bool = True) -> bool:
    """
    Click element with multiple fallback strategies.
    
    Args:
        driver: Selenium WebDriver instance
        element: WebElement to click
        max_retries: How many strategies to try
        scroll: Whether to scroll into view first
    
    Returns: True if successful, False if all strategies failed
    """
    if scroll:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                element
            )
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"Scroll failed: {e}")
    
    strategies = [
        ("action_chain", _click_via_action_chain),
        ("direct_click", _click_direct),
        ("js_click", _click_via_js),
        ("dispatch_event", _click_via_dispatch),
    ]
    
    for strategy_name, strategy_func in strategies[:max_retries]:
        try:
            if strategy_func(driver, element):
                return True
        except StaleElementReferenceException:
            logger.debug(f"Stale element in {strategy_name}")
            return False
        except Exception as e:
            logger.debug(f"Strategy {strategy_name} failed: {e}")
            continue
    
    logger.warning("All click strategies failed")
    return False


def _click_via_action_chain(driver, element) -> bool:
    """Strategy 1: ActionChains with movement + pause."""
    try:
        ActionChains(driver).move_to_element(element).pause(0.3).click().perform()
        return True
    except ElementNotInteractableException:
        return False


def _click_direct(driver, element) -> bool:
    """Strategy 2: Direct .click() method."""
    try:
        element.click()
        return True
    except (ElementNotInteractableException, ElementClickInterceptedException):
        return False


def _click_via_js(driver, element) -> bool:
    """Strategy 3: JavaScript click() (bypasses visibility checks)."""
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        return False


def _click_via_dispatch(driver, element) -> bool:
    """Strategy 4: Dispatch synthetic click event (last resort)."""
    try:
        driver.execute_script("""
            var event = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true,
            });
            arguments[0].dispatchEvent(event);
        """, element)
        return True
    except Exception:
        return False


def safe_open_in_new_tab(driver, url: str) -> bool:
    """
    Open URL in new tab (avoids losing current page).
    Useful when clicking job cards causes navigation issues.
    """
    try:
        # Open new tab
        driver.execute_script(f"window.open('{url}', '_blank');")
        time.sleep(0.5)
        
        # Switch to new tab
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            return True
        return False
    except Exception as e:
        logger.debug(f"Open new tab failed: {e}")
        return False


def close_current_tab_and_return(driver) -> bool:
    """Close current tab and switch back to first tab."""
    try:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return True
        return False
    except Exception as e:
        logger.debug(f"Close tab failed: {e}")
        return False