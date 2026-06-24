# 🔌 Plugin Specification

## Contract
Every extractor inherits `BaseExtractor`:

```python
class BaseExtractor(ABC):
    name: str
    base_url: str
    requires_login: bool = True
    supports_easy_apply: bool = True

    def __init__(self, driver, config, profile, answer_bank,
                 stealth_cfg, ai_provider=None, ai_config=None):
        ...

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

## Method Contracts

### `login()`
- Pre: fresh Chrome (may have cached cookies)
- Post: logged in (True) or LoginError
- 2FA: use `totp_secret` or wait 2 min for manual

### `search(filters)`
- Pre: logged in
- Post: on search results for `filters.queries[0]`
- Apply all filter knobs

### `collect_job_cards(max_cards)`
- Returns list of `{job_id, title, company, location, _element}`
- Lazy-scroll for more
- Dedupe by job_id

### `open_job_detail(card)`
- Returns full JobListing
- Side effect: navigates to detail

### `can_auto_apply(job)`
- Cheap check, no clicks
- Phase 1: `job.is_easy_apply`
- Phase 2+: + fit_score threshold

### `apply(job, resume_path, mode)`
- Walks modal up to 15 steps
- Stuck detect (2x same progress)
- Screenshot on failure
- Cleanup: close + discard draft

## Selectors
Centralize in module-level `SELECTORS` dict.

Preference order:
1. data-testid (most stable)
2. id
3. aria-label
4. CSS class chain
5. XPath with text (last resort)

## Multi-Language
LinkedIn extractor supports: EN/IT/ES/FR/DE/PT/NL.

Pattern:
```python
BTN_NEXT_LABELS = ["Next", "Avanti", ...]
SELECTORS["btn_next"] = (By.XPATH, _xpath_button_any(BTN_NEXT_LABELS))
```

## Adding New Platform

1. Create `packages/extractors/<name>.py`
2. Implement 6 methods
3. Register in `EXTRACTOR_REGISTRY` in `runner.py`
4. Add config block `platforms.<name>.*`
5. Add `.env` vars `<NAME>_EMAIL`, `<NAME>_PASSWORD`
6. Test with `mode: safe_auto`

See [PRDs/PRD_4*](PRDs/) for per-platform PRDs.
