"""Pre-apply filtering logic."""
import re
from rapidfuzz import fuzz


def title_passes(title: str, include: list[str], exclude: list[str]) -> tuple[bool, str]:
    t = (title or "").lower()
    for ex in exclude or []:
        if ex.lower() in t:
            return False, f"title contains excluded keyword: {ex}"
    if include:
        if not any(inc.lower() in t for inc in include):
            return False, f"title missing required keywords"
    return True, ""


def description_passes(description: str, exclude: list[str]) -> tuple[bool, str]:
    d = (description or "").lower()
    for kw in exclude or []:
        if kw.lower() in d:
            return False, f"description contains: {kw}"
    return True, ""


def company_passes(company: str, blacklist: list[str]) -> tuple[bool, str]:
    c = (company or "").lower()
    for b in blacklist or []:
        if b.lower() in c or fuzz.ratio(c, b.lower()) > 85:
            return False, f"company blacklisted: {b}"
    return True, ""


def salary_passes(salary_text: str, min_salary: int) -> tuple[bool, str]:
    if not min_salary or not salary_text:
        return True, ""
    nums = re.findall(r"[\d,]+", salary_text)
    nums = [int(n.replace(",", "")) for n in nums if n.replace(",", "").isdigit()]
    if nums and max(nums) < min_salary:
        return False, f"salary too low: {salary_text}"
    return True, ""
