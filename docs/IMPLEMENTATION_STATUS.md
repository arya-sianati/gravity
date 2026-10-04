# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 12 — Leaderboard Filtering & Scopes

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
- Phase 03 - Authentication & Profile
- Phase 04 - Configurable Activity Engine
- Phase 05 - Map Foundation
- Phase 06 - Activity Sessions
- Phase 07 - Live Map Heat
- Phase 08 - QR Joining
- Phase 09 - Realtime WebSockets
- Phase 10 - Metrics & Activity Leaderboards
- Phase 11 - Gravity XP & Levels
  - Built `XPTransaction` ledger model tracking history, reason, and context.
  - Implemented `xp_service.py` to deterministically allocate XP and calculate derived `level_for_xp` mathematically via bounded curves.
  - Integrated Participation XP completion hook into `leave` event with server-based minimum duration thresholds (`GRAVITY_MIN_XP_DURATION_SECONDS`).
  - Added idempotency protecting against duplicate participation XP using DB unique constraints.
  - Completed endpoints for `GET /api/me/xp-history/` and payload expansions for user profile logic.
  - Wired frontend `ProfileScreen.tsx` with dynamic level progression bar overlay.
  - Implemented realtime `+XP / Level Up!` toast overlay gracefully rendered directly across the `AppShell`.

## In progress
- None

## Known issues
- Phone-camera QR testing recorded as pending for deployment/demo hardening.

## Deferred
- Full privacy settings UI remains deferred to P1 / Phase 16 as approved.
- `season` period filtering on Leaderboards is intentionally returning 501 until Phase 14 implements Season logic.

## Setup / migration commands
```bash
# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt # (or directly via pip for now)
python manage.py migrate
python manage.py seed_gravity

# Setup frontend
cd frontend
npm install
npm run dev
```

## Next recommended task
Begin Phase 12: Leaderboard Filtering & Scopes.
