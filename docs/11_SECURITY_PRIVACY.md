# 🔐 Security & Privacy

## Threat Model
| Threat | Mitigation |
|---|---|
| Credentials in git | .gitignore + .env |
| LinkedIn detection | undetected-cd + humanizer |
| Account ban | rate caps + pauses |
| Stolen .env | P5 vault (AES-256) |
| AI sees PII | only candidate facts (no JD/resume in P2a) |

## Anti-Detection Layers
1. Browser fingerprint: `undetected-chromedriver`
2. Behavioral: `humanizer.py` (random delays, typing variance)
3. Rate limiting: caps + pauses
4. Session persistence: `.chrome-profile/`
5. Proxy rotation (P5)

## LinkedIn ToS
Section 8.2 prohibits automation.

**Reality**:
- Risk of restriction/ban is real
- Use throwaway account first
- Conservative caps on primary

**Best practices**:
1. Solve 2FA manually first run
2. safe_auto for first 10 applies
3. Don't run 24/7
4. Don't apply to duplicates
5. Respect human pace (≤25/day)

## Privacy Promises
**Local-only**:
- Resumes (base + tailored)
- Cover letters
- Applications + Q&A
- Browser cookies
- Credentials
- Logs + screenshots

**Outbound**:
- AI calls (if enabled, to YOUR endpoint)
- Webhooks if configured (P4)
- Notifications if configured (P3)

**Never sent**:
- LinkedIn cookies/session
- Other apps' data

## Audit Trail
| Action | Logged | Where |
|---|---|---|
| Login | Yes | bot.log |
| Apply submit | Yes | DB + bot.log |
| AI call | Yes | bot.log |
| AI answer save | Yes | answers.json + log |
| User UI action | P5 | audit_log table |

## 🔗 [10_CONFIGURATION_SPEC.md](10_CONFIGURATION_SPEC.md)
