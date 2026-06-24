# PRD: Phase 4f — Multi-Profile / Multi-Tenant

## 0. Status: ⏭️ PLANNED

## 1. Problem
Currently single user. Need multi-profile (e.g., personal + secondary account) and eventually multi-tenant (SaaS).

## 2. Goals
- ✅ Per-tenant data isolation: `data/<tenant>/`
- ✅ RBAC roles (admin / user / read-only)
- ✅ Encrypted credentials per tenant via vault (Phase 5)

## 3. Tech Spec
- `packages/security/rbac.py`
- DB: `tenants` + `profiles` tables
- Vault for per-tenant secrets
- UI: tenant switcher

## 4. Checklist
- [ ] Tenant model
- [ ] Data partition by tenant
- [ ] RBAC middleware
- [ ] Tenant switcher UI

## 5. Acceptance
- [ ] User A can't see User B's applications
- [ ] Per-tenant vault
