# 🛠️ Tech Stack

## Core
| Tech | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| Chrome | latest | Browser |
| Docker | latest | Optional packaging |

## Web
| Tech | Version | Purpose |
|---|---|---|
| Flask | 3.0.3 | Web UI |
| Jinja2 | bundled | Templates |
| Bootstrap | 5.3.3 CDN | Styling |
| FastAPI | TBD P4 | REST API |

## Automation
| Tech | Version | Purpose |
|---|---|---|
| undetected-chromedriver | 3.5.5 | Stealth |
| selenium | 4.25.0 | Browser control |
| pyautogui | 0.9.54 | Mouse jitter |

## Storage
| Tech | Version | Purpose |
|---|---|---|
| SQLite | bundled | Apps DB |
| SQLAlchemy | 2.0.35 | ORM |
| Postgres | 16 P5 | Future |
| Redis | 7 P5 | Control plane |

## AI
| Tech | Version | Purpose |
|---|---|---|
| openai | >=1.50.0 | OpenAI-compatible client |
| rapidfuzz | >=3.10.1 | Fuzzy match |
| reportlab | 4.2.5 | PDF generation |
| python-docx | 1.1.2 | Resume parse |

## Other
| Tech | Version | Purpose |
|---|---|---|
| pydantic | 2.9.2 | Validation |
| loguru | 0.7.2 | Logging |
| python-dotenv | 1.0.1 | .env |
| pyotp | 2.9.0 | 2FA |
| APScheduler | 3.10.4 | Cron (P3) |
| openpyxl | 3.1.5 | Excel export |

## Phase 5 additions
- cryptography (vault)
- keyring (master key)
- prometheus_client
- pytest, ruff, mypy, bandit, trivy

## 🔗 [10_CONFIGURATION_SPEC.md](10_CONFIGURATION_SPEC.md)
