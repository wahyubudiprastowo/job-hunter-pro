# 🎨 UI / UX Specification

## Site Map
```
/                    Dashboard (landing)
/applications        History table
/applications?status=<s>
/application/<id>    Detail
/questions           Q&A editor
/settings (P3)
/schedule (P3)
/analytics (P3)
/control/start, /pause, /resume, /stop
/api/state, /logs/tail, /diagnostics (P6)
/api/test-ai (P5)
/control/reset-state (P4)
```

## Dashboard Components (current state)
- State pill (idle/running/paused/stopped)
- Control: Start / Pause / Resume / Stop / **Reset State** / **Test AI**
- **🔧 Diagnostics card**:
  - State
  - Command (pending)
  - PID
  - Heartbeat age (seconds)
  - Is zombie (Yes/No)
- Stats: Applied / Skipped / Needs / Failed / External
- Live logs (5s poll)
- Unanswered queue (top 5)
- Recent applications table

## Color Palette
| Status | Class | Hex |
|---|---|---|
| applied | bg-success | #198754 |
| skipped | bg-secondary | #6c757d |
| failed | bg-danger | #dc3545 |
| needs_answers | bg-warning | #fd7e14 |
| external | bg-info | #0dcaf0 |
| running | state-running | green |
| paused | state-paused | orange |
| stopped | state-stopped | red |

## Real-time
- `/api/state` polled every 5s
- `/api/logs/tail` polled every 5s
- `/api/diagnostics` polled every 5s (P6+)

## Phase 3+ Planned
- HTMX for live updates (replace polling)
- SSE stream `/api/events`
- Dark mode toggle
- Fit score gauge per app
- Ghost status badge
- Health score on dashboard

## 🔗 [09_API_REFERENCE.md](09_API_REFERENCE.md)
