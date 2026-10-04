# Gravity — Implementation Status

Last updated: 2026-10-03

## Current phase
Phase 07 — Live Map Heat

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
- Phase 03 - Authentication & Profile
- Phase 04 - Configurable Activity Engine
- Phase 05 - Map Foundation
- Phase 06 - Activity Sessions
  - Implemented `ActivitySession` and `Participation` models using PostGIS.
  - Enforced single active participation logic per user.
  - Completed start, join, and leave session logic with `GET /api/sessions/nearby/` endpoint.
  - Upgraded frontend `StartActivityScreen` to handle nearby matching and `Other` label input.
  - Created live `ActiveActivityScreen` with client-side accurate elapsed timer.
  - Added test suites mapping constraints and REST APIs successfully.

## In progress
- None

## Known issues
- None

## Deferred
- Full privacy settings UI remains deferred to P1 / Phase 16 as approved.

## Setup / migration commands
```bash
# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
python manage.py migrate
python manage.py seed_gravity

# Setup frontend
cd frontend
npm install
npm run dev
```

## Next recommended task
Begin Phase 07: Live Map Heat.
