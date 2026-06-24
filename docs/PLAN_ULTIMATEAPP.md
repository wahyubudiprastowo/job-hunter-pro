# 🚀 Job-Hunter Pro — The "Ultimate" Edition

Kalau yang sebelumnya itu **v1.0 (super detailed)**, sekarang kita angkat ke level **v2.0 — Enterprise / Platform-grade**. Aku gabungin semua hal yang udah kamu suka dari project lain kamu (modular plugin architecture, ZTNA-style security, real-time monitoring, multi-tenant kayak SharePoint backup, anti-hallucination, DevSecOps pipeline) plus fitur unik yang belum ada di platform manapun.

Ini bukan sekadar bot — ini **personal career automation platform**.

***

## 🎯 Vision Statement

> Bukan "bot apply LinkedIn", tapi **end-to-end career operations platform** — discover → score → tailor → apply → track → analyze → follow-up — multi-platform, multi-profile, multi-tenant, runs locally first, deployable to cloud later.

***

## 🏛️ Architecture Overview (Layered + Modular)

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  Web UI (Flask+HTMX)  •  REST API (FastAPI)  •  WebSocket (SSE) │
│  CLI (Typer)          •  Telegram Bot       •  Webhook receiver │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│  Scheduler (APScheduler)  •  Queue (Redis/RQ)  •  Worker Pool   │
│  State Machine            •  Pause/Resume/Stop Controller       │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOMAIN / BUSINESS LAYER                       │
│  Job Discovery    •  Fit Scoring     •  Form Filling            │
│  Resume Tailor    •  Cover Letter    •  Question Handler        │
│  Ghosting Detect  •  Health Score    •  Interview Prep          │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PLUGIN / EXTENSION LAYER                        │
│  Extractors: LinkedIn, Indeed, Glassdoor, Wellfound, JobStreet  │
│  AI Providers: OpenAI, DeepSeek, Anthropic, Ollama (local)      │
│  Notifiers: Email, Telegram, Teams, Discord, Webhook            │
│  Captcha Solvers: 2Captcha, CapMonster, Manual-via-UI           │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                            │
│  Browser Pool (UC)  •  Proxy Rotator  •  Secrets Vault          │
│  Storage: SQLite/Postgres  •  Cache: Redis  •  Files: MinIO/FS  │
│  Audit Log          •  Metrics (Prometheus)  •  Tracing         │
└─────────────────────────────────────────────────────────────────┘
```

***

## 📁 Final Repository Structure (Monorepo)

```
job-hunter-pro/
├── apps/
│   ├── api/                    # FastAPI: REST + WebSocket
│   ├── web/                    # Flask + HTMX + Tailwind (or Next.js)
│   ├── worker/                 # Bot runner (Selenium + undetected-cd)
│   ├── scheduler/              # APScheduler with cron expressions
│   └── cli/                    # Typer CLI for power users
├── packages/
│   ├── core/                   # Pydantic models, enums, exceptions
│   ├── extractors/             # Plugin: BaseExtractor + implementations
│   │   ├── base.py
│   │   ├── linkedin.py
│   │   ├── indeed.py
│   │   ├── glassdoor.py
│   │   ├── wellfound.py
│   │   └── jobstreet.py
│   ├── ai/                     # All AI logic, provider-agnostic
│   │   ├── providers/          # openai.py, deepseek.py, anthropic.py, ollama.py
│   │   ├── tailor.py
│   │   ├── scorer.py           # ⭐ Job fit 0-100
│   │   ├── ghosting.py         # ⭐ Ghosting detector
│   │   ├── health.py           # ⭐ Application health score
│   │   ├── interview.py        # ⭐ Interview prep generator
│   │   └── question_bot.py     # Fuzzy + AI fallback
│   ├── notifications/
│   │   ├── base.py
│   │   ├── email.py, telegram.py, teams.py, discord.py, webhook.py
│   ├── stealth/
│   │   ├── browser.py
│   │   ├── humanizer.py        # Mouse curves, typing variance
│   │   ├── captcha.py          # 2Captcha + manual fallback
│   │   └── proxy_rotator.py
│   ├── storage/
│   │   ├── repositories/       # Repository pattern (Apps, Jobs, Q&A)
│   │   ├── models.py
│   │   └── migrations/         # Alembic
│   ├── security/
│   │   ├── vault.py            # Encrypted secrets (AES-256)
│   │   ├── audit.py
│   │   └── rbac.py             # multi-tenant role-based access
│   └── analytics/
│       ├── metrics.py
│       └── reports.py
├── plugins/                    # User-installable plugins (drop-in folder)
├── configs/
│   ├── profiles/               # per-tenant: alice.yaml, bob.yaml
│   ├── schemas/                # JSON Schema for runtime validation
│   └── defaults/
├── resumes/
│   ├── library/                # versioned base resumes
│   └── generated/
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.worker
│   │   ├── Dockerfile.web
│   │   └── docker-compose.yml
│   ├── k8s/                    # Helm chart (optional cloud deploy)
│   ├── terraform/              # Azure/AWS provisioning (optional)
│   └── ci/
│       ├── gitlab-ci.yml       # DevSecOps: Trivy, lint, test, deploy
│       └── azure-pipelines.yml
├── data/
│   ├── db/, files/, logs/, backups/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── DEVELOPMENT.md
│   ├── PLUGIN_GUIDE.md
│   ├── API.md                  # OpenAPI/Swagger auto-generated
│   └── adr/                    # Architectural Decision Records
├── tests/                      # pytest: unit, integration, e2e
├── scripts/
└── README.md
```

***

## 🆚 Feature Matrix: PoC → Pro → Enterprise

| Feature                                    | PoC (sebelumnya) | v1 (Super Detailed) |        **v2 Ultimate**       |
| ------------------------------------------ | :--------------: | :-----------------: | :--------------------------: |
| LinkedIn Easy Apply                        |         ✅        |          ✅          |               ✅              |
| Indeed / Glassdoor / Wellfound / JobStreet |         ❌        |          ❌          |        ✅ Plugin-based        |
| AI Resume Tailoring                        |         ❌        |       ✅ OpenAI      | ✅ Multi-provider + local LLM |
| AI Cover Letter                            |         ❌        |          ✅          |       ✅ + A/B variants       |
| **Job Fit Scoring (0–100)**                |         ❌        |          ❌          |              ⭐ ✅             |
| **Ghosting Detector**                      |         ❌        |          ❌          |              ⭐ ✅             |
| **Application Health Score**               |         ❌        |          ❌          |              ⭐ ✅             |
| **Interview Prep Generator**               |         ❌        |          ❌          |              ⭐ ✅             |
| Question Bank (fuzzy + AI fallback)        |      partial     |          ✅          |        ✅ + auto-learn        |
| Multi-profile / Multi-tenant               |         ❌        |          ❌          |            ✅ RBAC            |
| Real-time WebSocket UI                     |         ❌        |          ❌          |     ✅ + Pause/Resume/Stop    |
| Scheduler (cron)                           |         ❌        |          ❌          |         ✅ APScheduler        |
| Notifications hub                          |         ❌        |       partial       |         ✅ 5 channels         |
| CAPTCHA solver                             |         ❌        |          ❌          |    ✅ 2Captcha + manual UI    |
| Proxy rotation                             |         ❌        |          ❌          |               ✅              |
| Encrypted secrets vault                    |         ❌        |          ❌          |           ✅ AES-256          |
| Audit log (every action)                   |         ❌        |          ❌          |               ✅              |
| REST API + Swagger                         |         ❌        |          ❌          |           ✅ FastAPI          |
| Webhooks (outbound)                        |         ❌        |          ❌          |               ✅              |
| Backup / restore (encrypted)               |         ❌        |          ❌          |               ✅              |
| DevSecOps CI/CD (Trivy + ZTNA)             |         ❌        |          ❌          |     ✅ GitLab/Azure DevOps    |
| Dark mode + i18n (EN/ID)                   |         ❌        |          ❌          |               ✅              |
| PWA (mobile install)                       |         ❌        |          ❌          |               ✅              |

***

## ⭐ Featured New Modules (Code Highlights)

Aku gak ngulang semua kode v1 — fokus ke **fitur baru yang membedakan**.

### 1️⃣ `packages/ai/scorer.py` — Job Fit Score

```python
"""AI scores each job 0-100 against candidate profile."""
from pydantic import BaseModel
from .providers import get_provider

class FitScore(BaseModel):
    score: int                    # 0-100
    matched_skills: list[str]
    missing_skills: list[str]
    red_flags: list[str]
    reasoning: str
    recommendation: str           # "STRONG_APPLY" | "APPLY" | "MAYBE" | "SKIP"

SCORER_PROMPT = """You are a strict career coach. Score this job 0-100 for the candidate.

CANDIDATE FACTS (do NOT invent beyond this):
{candidate_facts}

JOB DESCRIPTION:
{job_description}

Rules:
- 90-100: perfect match, all required skills present
- 70-89: strong match, minor gaps
- 50-69: feasible but notable gaps
- <50: poor fit, skip

Return JSON: {{"score": int, "matched_skills": [...], "missing_skills": [...],
"red_flags": [...], "reasoning": "...", "recommendation": "..."}}"""

def score_job(candidate_facts: dict, job_description: str) -> FitScore:
    provider = get_provider()
    raw = provider.chat_json(
        SCORER_PROMPT.format(
            candidate_facts=candidate_facts,
            job_description=job_description[:5000]
        ),
        schema=FitScore
    )
    return FitScore(**raw)
```

**Use case:** Bot skip otomatis kalau `score < threshold` (configurable, default 60). Tampil sebagai badge berwarna di dashboard.

***

### 2️⃣ `packages/ai/ghosting.py` — Ghosting Detector ⭐

Fitur unik yang gak ada di Teal/Huntr.

```python
"""Detect if a company has ghosted you."""
from datetime import datetime, timedelta
from enum import Enum

class GhostStatus(str, Enum):
    ACTIVE = "active"             # < 7 days, normal
    SLOW = "slow"                 # 7-14 days
    LIKELY_GHOSTED = "likely_ghosted"   # 15-30 days no response
    GHOSTED = "ghosted"           # > 30 days
    REJECTED = "rejected"         # explicit reject received

def analyze_ghosting(application) -> dict:
    days_since = (datetime.utcnow() - application.applied_at).days
    has_view = application.viewed_by_recruiter
    has_response = application.last_response_at is not None

    if has_response and application.last_response_type == "REJECT":
        status = GhostStatus.REJECTED
    elif days_since > 30:
        status = GhostStatus.GHOSTED
    elif days_since > 14 and has_view and not has_response:
        status = GhostStatus.LIKELY_GHOSTED      # viewed but silent = red flag
    elif days_since > 7:
        status = GhostStatus.SLOW
    else:
        status = GhostStatus.ACTIVE

    return {
        "status": status,
        "days_since_applied": days_since,
        "should_followup": status in (GhostStatus.SLOW, GhostStatus.LIKELY_GHOSTED),
        "should_archive": status == GhostStatus.GHOSTED,
        "company_ghost_rate": _company_ghost_rate(application.company),
    }

def _company_ghost_rate(company: str) -> float:
    """% of applications to this company that ended up ghosted (community data)."""
    # Aggregated across all your applications to that company
    ...
```

**UI representation:** kolom badge di history table — 🟢 Active / 🟡 Slow / 🟠 Likely Ghosted / ⚫ Ghosted / 🔴 Rejected, plus **"Company Ghost Rate: 78%"** sebagai warning sebelum apply lagi.

***

### 3️⃣ `packages/ai/health.py` — Application Health Score ⭐

```python
"""Overall pipeline health 0-100."""
def calculate_health_score(stats: dict) -> dict:
    factors = {
        "application_velocity": _score_velocity(stats),       # apps/week
        "response_rate": _score_response_rate(stats),         # responses/apps
        "interview_conversion": _score_interview_rate(stats), # interviews/responses
        "ghost_rate_penalty": _ghost_penalty(stats),          # negative
        "diversity_bonus": _diversity_bonus(stats),           # multiple companies/levels
        "ai_quality_score": _resume_quality(stats),           # tailored vs generic
    }
    weighted = (
        factors["application_velocity"] * 0.15 +
        factors["response_rate"] * 0.30 +
        factors["interview_conversion"] * 0.30 +
        factors["diversity_bonus"] * 0.10 +
        factors["ai_quality_score"] * 0.15 -
        factors["ghost_rate_penalty"] * 0.20
    )
    return {
        "score": max(0, min(100, int(weighted))),
        "factors": factors,
        "advice": _generate_advice(factors),
    }
```

Tampil di dashboard sebagai **big circular gauge** + actionable advice ("Response rate kamu turun 20% minggu ini — coba refresh resume summary").

***

### 4️⃣ `packages/ai/interview.py` — Interview Prep ⭐

Begitu status job → `INTERVIEW_SCHEDULED`, bot auto-generate:

```python
def generate_interview_pack(job, candidate_facts) -> dict:
    return {
        "likely_questions": _predict_questions(job),       # 15-20 STAR-format
        "your_answers_draft": _draft_answers(job, candidate_facts),
        "questions_to_ask": _generate_smart_questions(job),
        "company_research": _research_summary(job.company),
        "salary_negotiation_data": _negotiation_brief(job),
        "red_flags_to_clarify": _detect_red_flags(job),
    }
```

Output: 1 PDF "Interview Pack" siap pakai per job.

***

### 5️⃣ `packages/security/vault.py` — Encrypted Secrets

```python
"""AES-256 encrypted secrets at rest. Master key from OS keyring."""
from cryptography.fernet import Fernet
import keyring

class Vault:
    KEYRING_SERVICE = "job-hunter-pro"

    def __init__(self):
        key = keyring.get_password(self.KEYRING_SERVICE, "master")
        if not key:
            key = Fernet.generate_key().decode()
            keyring.set_password(self.KEYRING_SERVICE, "master", key)
        self.cipher = Fernet(key.encode())

    def put(self, name: str, value: str) -> None:
        encrypted = self.cipher.encrypt(value.encode())
        _db.execute("INSERT OR REPLACE INTO secrets VALUES (?,?)", (name, encrypted))

    def get(self, name: str) -> str | None:
        row = _db.execute("SELECT value FROM secrets WHERE name=?", (name,)).fetchone()
        return self.cipher.decrypt(row[0]).decode() if row else None
```

**Manfaat:** LinkedIn password, OpenAI key, Telegram token — semua encrypted on disk, never in plaintext config.

***

### 6️⃣ `packages/extractors/base.py` — Plugin Architecture

```python
"""Every job platform = a plugin implementing this interface."""
from abc import ABC, abstractmethod
from packages.core.models import JobListing, ApplicationResult

class BaseExtractor(ABC):
    name: str
    base_url: str
    requires_login: bool = True

    @abstractmethod
    def login(self, credentials) -> bool: ...

    @abstractmethod
    def search(self, filters) -> list...

    @abstractmethod
    def get_details(self, job: JobListing) -> JobListing: ...

    @abstractmethod
    def can_easy_apply(self, job: JobListing) -> bool: ...

    @abstractmethod
    def apply(self, job: JobListing, profile, answer_bank) -> ApplicationResult: ...

    @abstractmethod
    def get_application_status(self, job_id: str) -> str: ...
```

User mau tambah Indeed? Tinggal drop `packages/extractors/indeed.py` yang implement interface ini. **Zero changes to core code.** Sesuai preferensi pluggable kamu.

***

### 7️⃣ Real-time UI Controls (Pause/Resume/Stop)

State machine yang **benar-benar respect** sinyal control:

```python
# apps/worker/state_machine.py
class WorkerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"

class WorkerController:
    """Singleton accessible via Redis pub/sub so UI commands take effect immediately."""
    
    async def check_signals(self):
        """Called between every job — respects pause/stop instantly."""
        cmd = await redis.get(f"worker:{self.id}:command")
        if cmd == "PAUSE":
            self.state = WorkerState.PAUSED
            await self._broadcast_state()
            while await redis.get(f"worker:{self.id}:command") == "PAUSE":
                await asyncio.sleep(1)
        if cmd == "STOP":
            raise WorkerStopSignal()
```

Frontend SSE stream:

```
event: progress
data: {"current_job": "Cloud Engineer @ Microsoft", "progress": 47, "total": 50}

event: state_change
data: {"state": "PAUSED"}

event: question_needs_input
data: {"question": "What is your highest TOEFL score?", "job_id": "..."}
```

***

### 8️⃣ Notifications Hub

```python
# packages/notifications/base.py
class NotificationEvent(BaseModel):
    type: Literal["applied","skipped","captcha","error","milestone","ghost_detected"]
    title: str
    body: str
    data: dict

class NotificationHub:
    def __init__(self, channels: list[BaseNotifier]):
        self.channels = channels

    async def emit(self, event: NotificationEvent):
        for ch in self.channels:
            if event.type in ch.subscribed_events:
                try:
                    await ch.send(event)
                except Exception as e:
                    logger.warning(f"{ch.name} failed: {e}")
```

Channel: **Email, Telegram, Teams (webhook), Discord, Generic Webhook**. Granular per-event subscription di config.

***

### 9️⃣ DevSecOps Pipeline (`infra/ci/gitlab-ci.yml`)

```yaml
stages: [lint, test, scan, build, deploy]

lint:
  script:
    - ruff check .
    - mypy packages/
    - bandit -r packages/ apps/

test:
  script:
    - pytest --cov=packages --cov=apps --cov-report=xml
    - coverage report --fail-under=80

trivy-scan:
  stage: scan
  script:
    - trivy fs --severity HIGH,CRITICAL --exit-code 1 .
    - trivy image $IMAGE_TAG --severity HIGH,CRITICAL

build:
  script:
    - docker buildx build --platform linux/amd64,linux/arm64 -t $IMAGE_TAG .

deploy-staging:
  environment: { name: staging, url: https://staging.jobhunter.local }
  when: manual

deploy-prod:
  environment: { name: production }
  when: manual
  needs: [deploy-staging]
  before_script:
    - ./scripts/ztna-tunnel.sh up
```

Persis pattern yang biasa kamu request: lint → test → Trivy scan → build → staging → manual approval → prod via ZTNA tunnel.

***

## 🐳 Updated `docker-compose.yml` (Production-grade)

```yaml
services:
  api:
    build: { context: ., dockerfile: infra/docker/Dockerfile.api }
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    env_file: .env
    healthcheck:
      test: ["CMD","curl","-f","http://localhost:8000/health"]

  web:
    build: { context: ., dockerfile: infra/docker/Dockerfile.web }
    ports: ["5050:5050"]
    depends_on: [api]

  worker:
    build: { context: ., dockerfile: infra/docker/Dockerfile.worker }
    depends_on: [api, redis]
    shm_size: "2g"
    volumes:
      - chrome-profiles:/app/.chrome-profiles
      - ./resumes:/app/resumes
    deploy:
      replicas: 2          # multi-worker for parallel apply across profiles

  scheduler:
    build: { context: ., dockerfile: infra/docker/Dockerfile.worker }
    command: python -m apps.scheduler
    depends_on: [redis]

  postgres:
    image: postgres:16-alpine
    volumes: [pg-data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: jobhunter
      POSTGRES_USER: jobhunter
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]

  redis:
    image: redis:7-alpine
    volumes: [redis-data:/data]

  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes: [./infra/prometheus.yml:/etc/prometheus/prometheus.yml:ro]

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    volumes: [grafana-data:/var/lib/grafana]

volumes: { pg-data: , redis-data: , chrome-profiles: , grafana-data: }
secrets:
  db_password: { file: ./secrets/db_password.txt }
```

***

## 📊 Updated Data Model (Postgres + SQLAlchemy)

Tambahan tabel kunci:

| Table               | Purpose                               |
| ------------------- | ------------------------------------- |
| `tenants`           | multi-tenant root                     |
| `profiles`          | candidate profiles per tenant         |
| `resume_versions`   | versioned base resumes                |
| `jobs`              | discovered jobs (deduped global pool) |
| `applications`      | per-profile application records       |
| `fit_scores`        | scoring history per (profile, job)    |
| `interview_packs`   | generated prep materials              |
| `ghosting_signals`  | per-company ghost rate                |
| `notifications_log` | sent notifications audit              |
| `audit_log`         | every state-changing action           |
| `secrets`           | encrypted vault                       |
| `worker_runs`       | run history with metrics              |
| `question_bank`     | learned Q\&A with embedding vector    |
| `unanswered_queue`  | needs human input                     |
| `schedules`         | cron schedules per profile            |
| `proxies`           | proxy pool with health                |

***

## 🛣️ Phased Delivery Roadmap

Realistis — gak mungkin bangun semua sekaligus. Aku saranin **5 fase** dengan deliverable jelas:

### **Phase 0 — PoC** ✅ (sudah selesai)

Single-file bot, login → apply 1 job → SQLite log.

### **Phase 1 — MVP Web (2 minggu)**

* Migrate ke struktur monorepo
* Flask + HTMX UI: dashboard, history, question bank editor
* Pause/Resume/Stop via Redis pub/sub
* SQLite → Postgres migration via Alembic
* Docker compose untuk dev

### **Phase 2 — AI Pro (2 minggu)**

* Resume tailor + cover letter (OpenAI + DeepSeek + local Ollama)
* Job Fit Scorer
* Auto-skip jika score < threshold
* AI fallback untuk unknown questions
* Resume version library (multiple bases per role type)

### **Phase 3 — Differentiators (3 minggu)** ⭐

* Ghosting Detector + Company Ghost Rate
* Application Health Score dengan advice
* Interview Prep Pack generator
* Scheduler (cron jobs per profile)
* Notifications hub (Telegram + Teams + Email)
* CAPTCHA solver (2Captcha + manual UI)

### **Phase 4 — Multi-platform (3 minggu)**

* Plugin architecture extractors
* Indeed + Glassdoor + Wellfound + JobStreet
* Multi-profile & multi-tenant + RBAC
* Encrypted secrets vault
* REST API + Swagger
* Webhook outbound

### **Phase 5 — Enterprise (2 minggu)**

* DevSecOps CI/CD (GitLab + Trivy + ZTNA)
* Prometheus + Grafana metrics
* Audit log + backup/restore (encrypted)
* Helm chart untuk K8s deploy
* Dark mode + i18n (EN/ID)
* PWA installable

**Total realistic timeline: \~12 minggu** kalau part-time. Bisa lebih cepat kalau fokus.

***

## ✅ Final Acceptance Criteria (v2)

* [ ] `docker compose up` → semua service healthy < 90s
* [ ] Apply ke ≥ 20 jobs LinkedIn dalam 1 run tanpa terdeteksi
* [ ] Job Fit Score muncul di history dengan reasoning yang explainable
* [ ] Ghosting Detector flag minimal 1 application dalam 30 hari
* [ ] Pause dari UI → bot stop dalam ≤ 3 detik (cek antar-job)
* [ ] Resume tailored beda dari base (verified via diff)
* [ ] **0 hardcoded secrets**, semua via vault
* [ ] Audit log capture semua action user + bot
* [ ] CI pipeline green: lint + test + Trivy + 80% coverage
* [ ] Notification masuk ke Telegram/Teams dalam ≤ 5 detik dari event
* [ ] REST API documented via Swagger di `/docs`
* [ ] Dark mode toggle berfungsi, i18n EN/ID lengkap

***

## 🎁 Bonus: Unique Selling Points vs Kompetitor

| Kompetitor                         | Yang mereka punya | Yang kita tambah                          |
| ---------------------------------- | ----------------- | ----------------------------------------- |
| **Teal**                           | Tracker manual    | Auto-apply + AI tailor + Ghost detector   |
| **Huntr**                          | Kanban board      | Real-time bot + multi-platform            |
| **JobScan**                        | Resume scoring    | + actual application + interview prep     |
| **Apllie (wodsuz)**                | Chrome ext + bot  | + multi-tenant + analytics + DevSecOps    |
| **Auto\_job\_applier (GodsScion)** | LinkedIn bot      | + Indeed/Glassdoor + scheduler + REST API |

***


