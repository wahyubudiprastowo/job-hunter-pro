# PRD: Phase 4g — REST API (FastAPI)

## 0. Status: ⏭️ PLANNED

## 1. Problem
External tools / mobile / integrations need API.

## 2. Goals
- ✅ All UI actions exposed via REST
- ✅ Auto-generated OpenAPI at /docs
- ✅ API key auth
- ✅ Outbound webhooks

## 3. Tech Spec
- `apps/api/` (new) — FastAPI app
- Uvicorn ASGI server
- API key in `Authorization: Bearer`
- Webhook outbound on events

## 4. Endpoints
See [09_API_REFERENCE.md](../09_API_REFERENCE.md) section "REST API (Phase 4)".

## 5. Checklist
- [ ] FastAPI app
- [ ] All endpoints implemented
- [ ] API key auth
- [ ] OpenAPI docs at /docs
- [ ] Webhook outbound

## 6. Acceptance
- [ ] Curl test for all endpoints
- [ ] OpenAPI valid
- [ ] Webhook fires on events
