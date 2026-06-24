# 🐳 DevOps & CI/CD

## Docker

### Dockerfile (Phase 1+)
- Base: `python:3.11-slim-bookworm` (NOT trixie — package broken)
- libgdk-pixbuf-2.0-0 (dash!) NOT libgdk-pixbuf2.0-0
- chromium + chromium-driver + Xvfb
- WORKDIR /app, CMD python run_web.py

### docker-compose.yml
- Single service initially (Phase 5 splits into api/web/worker)
- shm_size: 2g (Chrome needs)
- Volumes: data/, resumes/, cover_letters/, chrome-profile

## Deployment Modes
1. **Native** (Windows/macOS/Linux) — first setup + 2FA
2. **Docker local** — after session cached
3. **Docker remote** (Phase 5) — Caddy/Traefik for HTTPS
4. **Kubernetes** (Phase 5) — Helm in `infra/k8s/`

## CI/CD (Phase 5)
`.gitlab-ci.yml` stages: lint → test → scan (Trivy) → build → deploy
- ruff, mypy, bandit
- pytest, coverage ≥ 80%
- Trivy HIGH+CRITICAL
- buildx multi-arch
- Staging manual gate
- Prod via ZTNA tunnel

## 🔗 [03_TECH_STACK.md](03_TECH_STACK.md)
