# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 13 — Gravity Events

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
- Phase 12 - Badges & Consistency
  - Added models `Badge`, `UserBadge`, `Streak`.
  - Constructed strictly decoupled evaluation logic in `achievement_service.py` and `streak_service.py`.
  - Registered idempotent completion response merging streak state, awarded XP, and newly earned badges in the same REST sequence natively.
  - Profile updated displaying dynamic Streak metrics, Longest Streak bounds, and visual array of earned badges.
  - Safe seeding configuration injected enabling administrator overrides to persist safely via `seed_badges`.

## In progress
- None

## Known issues
- Phone-camera QR testing recorded as pending for deployment/demo hardening.

## Deferred
- Full privacy settings UI remains deferred to P1 / Phase 16 as approved.

## Setup / migration commands
```bash
# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_gravity
python manage.py seed_badges

# Setup frontend
cd frontend
npm install
npm run dev
```

## Next recommended task
Begin Phase 13: Gravity Events.
