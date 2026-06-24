# PRD: Phase 5 — Enterprise (CI/CD, Postgres, Vault, K8s, i18n, PWA)

## 0. Status: ⏭️ PLANNED

## 1. Problem
Going from personal tool to production-grade platform.

## 2. Goals
- ✅ DevSecOps CI/CD (GitLab + Trivy + ZTNA)
- ✅ Postgres migration (Alembic)
- ✅ Prometheus + Grafana monitoring
- ✅ AES-256 vault
- ✅ Helm chart for K8s
- ✅ Dark mode + i18n EN/ID
- ✅ PWA installable

## 3. Tech Spec
- See [14_DEVOPS_CICD.md](../14_DEVOPS_CICD.md) for CI/CD
- See [03_TECH_STACK.md](../03_TECH_STACK.md) Phase 5 entries
- Migration plan: SQLite → Postgres via Alembic
- Vault: `packages/security/vault.py` with cryptography.Fernet + keyring

## 4. Checklist
- [ ] GitLab CI pipeline green
- [ ] Trivy scan integrated
- [ ] Postgres migration scripts
- [ ] Vault module
- [ ] Prometheus exporter
- [ ] Grafana dashboards
- [ ] Helm chart
- [ ] Dark mode toggle
- [ ] i18n EN/ID
- [ ] PWA manifest

## 5. Acceptance
- [ ] CI green (lint + test + Trivy + 80% coverage)
- [ ] Postgres in docker-compose works
- [ ] Metrics scrapeable
- [ ] K8s helm install works
- [ ] PWA installable on mobile
