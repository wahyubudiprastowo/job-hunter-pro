# Rate Limit Incident And Recovery Plan

Incident date: 2026-06-24  
Purpose: preserve incident context, lessons learned, and recovery guidance.

## What Happened

LinkedIn triggered anti-bot / rate-limit behavior after heavy usage across multiple runs in a short period.

Observed symptoms documented at the time:

- apply flow became unreliable
- some apply actions were blocked or disabled
- LinkedIn surfaced language consistent with daily submission limiting

## Why This Document Exists

This file was imported selectively from the v3.3 docs bundle because the operational lessons are still valuable even if the exact cooldown window has already passed.

## Likely Root Causes

1. Too many applies in a short window.
2. Multiple runs on the same day.
3. Repetitive timing / automation rhythm.
4. Not enough persistent per-day safety logic in code.

## Safe Recovery Guidance

If the same incident happens again:

1. Stop the bot from the dashboard.
2. Save current logs and screenshots.
3. Do not keep retrying aggressively.
4. Reduce run size and daily volume temporarily.
5. Resume with a small test run only after manual verification.

## Engineering Lessons

The incident strongly supports adding a real smart rate limiter:

- daily cap tracking
- per-platform persistence
- detection of rate-limit messages
- auto-pause / cooldown behavior
- dashboard visibility

See [PRDs/PRD_SmartRateLimiter.md](PRDs/PRD_SmartRateLimiter.md).

## Operational Note

This document is historical context, not proof that the account is currently rate-limited.
Always use current logs, UI, and observed LinkedIn behavior to decide whether cooldown is still active.
