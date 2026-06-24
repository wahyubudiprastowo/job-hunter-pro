# 📖 Glossary

| Term | Definition |
|---|---|
| Answer Bank | `data/answers.json` — Q→A map |
| Apply Status | Enum: applied/skipped/failed/needs_answers/external |
| ATS | Applicant Tracking System (Workday, Greenhouse, etc.) |
| BaseExtractor | Abstract class for platform plugins |
| Candidate Profile | User's personal info |
| Control Plane | File-based signaling (Pause/Resume/Stop) |
| **Diagnostics** | Dashboard panel: state/command/PID/heartbeat/zombie (Patch 6) |
| EEOC | US diversity questions (gender, race, disability, veteran) |
| Easy Apply | LinkedIn 1-click apply |
| Extractor | Platform-specific plugin |
| Fit Score | AI-generated 0-100 job-candidate match (P2d) |
| Ghost Status | Application response state (active/slow/likely_ghosted/...) |
| **Heartbeat** | Worker liveness signal (Patch 7) |
| Humanizer | Random delays + typing variance |
| **Is Zombie** | Worker dead (heartbeat too old) (Patch 6) |
| JD | Job Description |
| JobListing | Pydantic model with full job details |
| Mode | full_auto / semi_auto / safe_auto |
| OmniRouter | OpenAI-compatible AI gateway |
| Patch | Self-contained ZIP that updates files |
| Persistence Profile | `.chrome-profile/` cookies cache |
| **PID** | Process ID of worker (Patch 6) |
| Question Bank | Synonym for Answer Bank |
| **Reset State** | Button that clears state files (Patch 4) |
| SAFE MODE | safe_auto — pause before each Submit |
| Screener Question | Custom question on application form |
| SSE | Server-Sent Events (P3) |
| Stealth Mode | undetected-chromedriver + humanizer |
| Stuck Detection | Auto-abort on 2x same progress |
| **Test AI** | Button that pings AI provider (Patch 5) |
| TOTP | Time-based One-Time Password |
| Unanswered Queue | `data/unanswered.json` |
| Vault | Encrypted secrets (P5) |
| ZTNA | Zero Trust Network Access (P5) |
