# 🗺️ Roadmap

## ✅ Phase 1 (this release) — MVP
- BaseExtractor interface
- LinkedIn Easy Apply
- Flask dashboard
- SQLite history
- Fuzzy answer bank
- Pause/Resume/Stop
- Docker Compose

## ⏭️ Phase 2 — AI Tailoring (2 weeks)
- [ ] OpenAI integration (`packages/ai/`)
- [ ] Resume tailoring per job (PDF generation)
- [ ] Cover letter auto-generation
- [ ] Job Fit Score (0-100) per job
- [ ] AI fallback for unknown screener questions
- [ ] Auto-skip low-fit jobs (configurable threshold)
- [ ] Anti-hallucination rules (never invent experience)

## ⏭️ Phase 3 — Differentiators (3 weeks)
- [ ] **Ghosting Detector** (per-company ghost rate)
- [ ] **Application Health Score** with actionable advice
- [ ] **Interview Prep Pack** generator
- [ ] APScheduler cron-style scheduling
- [ ] Notifications: Email, Telegram, Teams, Discord, Webhook
- [ ] CAPTCHA solver (2Captcha integration)
- [ ] Manual CAPTCHA via UI fallback

## ⏭️ Phase 4 — Multi-platform (3 weeks)
- [ ] Indeed extractor
- [ ] Glassdoor extractor
- [ ] JobStreet extractor (Indonesia/SEA)
- [ ] Wellfound extractor
- [ ] Greenhouse + Lever ATS detection/handling
- [ ] Multi-profile / multi-tenant
- [ ] RBAC (role-based access)
- [ ] Encrypted secrets vault (AES-256)
- [ ] REST API (FastAPI + Swagger)
- [ ] Outbound webhooks

## ⏭️ Phase 5 — Enterprise (2 weeks)
- [ ] DevSecOps CI/CD (GitLab + Trivy + ZTNA)
- [ ] Prometheus + Grafana
- [ ] Postgres migration (Alembic)
- [ ] Audit log
- [ ] Backup/restore (encrypted)
- [ ] Helm chart for K8s
- [ ] Dark mode + i18n (EN/ID)
- [ ] PWA (mobile installable)

## Timeline
- Realistic part-time delivery: ~12 weeks total
- Aggressive full-time: ~6 weeks total

## Priority Order
For your job hunt context (Cloud/DevOps role, Indonesia-based):
1. **Phase 2 AI tailoring** — biggest leverage per application
2. **Phase 3 scheduler + notifications** — daily automation
3. **Phase 4 JobStreet + Indeed** — coverage for Indonesia
4. **Phase 3 Ghosting/Health/Interview** — pipeline visibility
5. **Phase 5 Enterprise** — only if open-sourcing
