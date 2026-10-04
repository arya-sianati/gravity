# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 10 — Metrics & Leaderboards

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
  - Configured Django Channels with Redis (`channels_redis`).
  - Added MapConsumer allowing anonymous connects for map-refresh broadcast.
  - Added SessionConsumer requiring authenticated scopes for specific session groups.
  - Tied `post_save` / `post_delete` signals on `ActivitySession` and `Participation` to `transaction.on_commit()` for 100% reliable broadcast.
  - Upgraded frontend to connect React `useGravitySocket` hook with visibility backoff and bounding polling fallback.
  - Preserved Phase 07 serialization privacy.

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
pip install -r requirements.txt # (or directly via pip for now)
python manage.py migrate
python manage.py seed_gravity

# Setup frontend
cd frontend
npm install
npm run dev
```

## Next recommended task
Begin Phase 10: Metrics & Leaderboards.
