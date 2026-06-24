# 🔌 Plugin Development Guide

How to add support for a new platform (Indeed, Glassdoor, JobStreet, Wellfound, etc.)
**without touching any other file in the codebase.**

## The Interface

Every extractor inherits `BaseExtractor` (`packages/extractors/base.py`):

```python
class BaseExtractor(ABC):
    name: str                  # short id, e.g. "indeed"
    base_url: str
    requires_login: bool = True
    supports_easy_apply: bool = True

    def __init__(self, driver, config, profile, answer_bank, stealth_cfg): ...

    @abstractmethod
    def login(self, email, password, totp_secret="") -> bool: ...

    @abstractmethod
    def search(self, filters: SearchFilters) -> None: ...

    @abstractmethod
    def collect_job_cards(self, max_cards=50) -> list[dict]: ...

    @abstractmethod
    def open_job_detail(self, card: dict) -> JobListing: ...

    @abstractmethod
    def can_auto_apply(self, job: JobListing) -> bool: ...

    @abstractmethod
    def apply(self, job, resume_path, mode="semi_auto") -> ApplicationResult: ...
```

## Step-by-Step: Adding Indeed

### 1. Create `packages/extractors/indeed.py`

```python
from packages.extractors.base import BaseExtractor
from packages.core.models import (
    SearchFilters, JobListing, ApplicationResult, ApplyStatus
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from packages.stealth.humanizer import human_sleep, type_human


class IndeedExtractor(BaseExtractor):
    name = "indeed"
    base_url = "https://www.indeed.com"
    supports_easy_apply = True

    def login(self, email, password, totp_secret=""):
        self.driver.get(f"{self.base_url}/account/login")
        # ... Indeed login flow ...
        return True

    def search(self, filters: SearchFilters) -> None:
        q = filters.queries[0]
        url = f"{self.base_url}/jobs?q={q}&l={filters.location}"
        if filters.easy_apply_only:
            url += "&iafilter=1"
        self.driver.get(url)
        human_sleep(3, 5)

    def collect_job_cards(self, max_cards=50):
        nodes = self.driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
        cards = []
        for n in nodes[:max_cards]:
            cards.append({
                "job_id": n.get_attribute("data-jk"),
                "title": n.find_element(By.CSS_SELECTOR, "h2 a span").text,
                "company": n.find_element(By.CSS_SELECTOR, "[data-testid='company-name']").text,
                "location": n.find_element(By.CSS_SELECTOR, "[data-testid='text-location']").text,
                "_element": n,
            })
        return cards

    def open_job_detail(self, card):
        card["_element"].click()
        human_sleep(2, 3)
        # ... extract description, salary, etc ...
        return JobListing(
            platform=self.name,
            job_id=card["job_id"],
            title=card["title"],
            company=card["company"],
            location=card["location"],
            url=f"{self.base_url}/viewjob?jk={card['job_id']}",
            description="...",
            is_easy_apply=True,
        )

    def can_auto_apply(self, job):
        return job.is_easy_apply

    def apply(self, job, resume_path, mode="semi_auto"):
        # ... fill Indeed Apply iframe ...
        return ApplicationResult(status=ApplyStatus.APPLIED)
```

### 2. Register in the orchestrator

```python
# apps/worker/runner.py
from packages.extractors.indeed import IndeedExtractor

EXTRACTOR_REGISTRY = {
    "linkedin": LinkedInExtractor,
    "indeed": IndeedExtractor,   # ← add
}
```

### 3. Add config block

```yaml
# config.yaml
platforms:
  indeed:
    enabled: true
    max_apply_per_run: 10
    search:
      queries: ["DevOps Engineer"]
      location: "Jakarta, Indonesia"
      remote: true
      date_posted: "past_week"
      easy_apply_only: true
```

### 4. Add credentials

```env
# .env
INDEED_EMAIL=...
INDEED_PASSWORD=...
```

That's it. The orchestrator handles everything else: filtering, deduplication,
storage, UI, pause/resume, unanswered questions.

## Tips & Gotchas Per Platform

| Platform | Gotchas |
|---|---|
| **Indeed** | Very aggressive CAPTCHA (hCaptcha). Use real residential IP if possible. Apply form is in an iframe. |
| **Glassdoor** | Login uses Indeed credentials internally. DOM very similar to Indeed. |
| **Wellfound** | Each company has custom Q&A. Use AI fallback (Phase 2). |
| **JobStreet** | SEA-focused; fewer Easy Apply jobs but cleaner DOM. Good Indonesia option. |
| **Workday ATS** | Different URL per company; needs a sub-router. Each company's Workday has its own DOM. Skip in Phase 1-2. |

## Reusing Logic Across Extractors

Common helpers should go in `packages/extractors/_common.py` (create when needed):

```python
def safe_text(element, selector): ...
def click_with_retry(driver, locator, retries=3): ...
def upload_file_to_iframe(driver, iframe, file_path): ...
```

Don't put platform-specific logic in shared helpers — keep extractors independent.
