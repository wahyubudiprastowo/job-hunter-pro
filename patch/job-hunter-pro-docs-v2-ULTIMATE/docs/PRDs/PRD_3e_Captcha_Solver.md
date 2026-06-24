# PRD: Phase 3e — CAPTCHA Solver

## 0. Status: ⏭️ PLANNED

## 1. Problem
LinkedIn and Indeed challenge users with CAPTCHAs. Bot must handle gracefully without ban.

## 2. Goals
- ✅ Auto-solve common types via 2Captcha
- ✅ Manual fallback via UI alert
- ✅ Pause + notify on detection

## 3. Tech Spec
- `packages/stealth/captcha.py` (new)
- 2Captcha API integration
- Detection: page content + URL pattern
- Manual mode: screenshot to UI + form for solution input

## 4. Anti-Detection
- Don't retry too fast (rate limit detection)
- Pause bot for N minutes after solve

## 5. Checklist
- [ ] Detection logic
- [ ] 2Captcha integration
- [ ] Manual UI fallback
- [ ] Pause-on-captcha mechanism

## 6. Acceptance
- [ ] Detected captcha triggers handler
- [ ] 2Captcha solves common types
- [ ] Manual mode shows screenshot in UI
