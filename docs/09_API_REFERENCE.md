# 🔗 API Reference

## Web Routes (current)

### Pages
| Method | Path | Purpose |
|---|---|---|
| GET | / | Dashboard |
| GET | /applications | History |
| GET | /applications?status=<s> | Filtered |
| GET | /application/<id> | Detail |
| GET | /questions | Q&A editor |
| POST | /questions | Add Q&A |
| POST | /questions/delete | Remove |
| POST | /questions/clear-unanswered | Clear queue |

### Control
| Path | Action |
|---|---|
| POST /control/start | Spawn worker |
| POST /control/pause | Write command=pause |
| POST /control/resume | Write command=resume |
| POST /control/stop | Write command=stop |
| POST /control/reset-state | Clear state files (P4) |

### JSON / Plain APIs
| Method | Path | Returns |
|---|---|---|
| GET | /api/state | `{state, stats}` |
| GET | /api/logs/tail | plain text last 100 lines |
| GET | /api/diagnostics | `{state, command, pid, heartbeat_age, is_zombie}` (P6) |
| POST | /api/test-ai | `{status, model, response_time}` (P5) |
| GET | /api/screenshots/<job_id> | list (P3+) |
| GET | /api/events | SSE stream (P3+) |

## REST API (Phase 4 — FastAPI)
OpenAPI at /docs. See [PRDs/PRD_4g_REST_API.md](PRDs/PRD_4g_REST_API.md).

Auth: `Authorization: Bearer <api_key>`.

Endpoints (planned):
- GET /api/v1/applications
- GET /api/v1/applications/{id}
- POST /api/v1/runs
- GET /api/v1/runs/{id}
- POST /api/v1/answers
- DELETE /api/v1/answers/{key}
- GET /api/v1/health

## Webhooks (P4 outbound)
Config:
```yaml
webhooks:
  - url: https://hooks.slack.com/...
    events: [applied, failed, milestone]
    secret: <HMAC>
```

Payload:
```json
{"event": "applied", "timestamp": "...", "data": {...}}
```

## 🔗 [06_UI_UX_SPEC.md](06_UI_UX_SPEC.md)
