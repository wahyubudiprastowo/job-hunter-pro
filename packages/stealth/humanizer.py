"""Human-like timing helpers."""
import random
import time


def human_sleep(min_s: float = 1.5, max_s: float = 4.5):
    time.sleep(random.uniform(min_s, max_s))


def type_human(element, text: str, min_d: float = 0.05, max_d: float = 0.15):
    for ch in str(text):
        element.send_keys(ch)
        time.sleep(random.uniform(min_d, max_d))
