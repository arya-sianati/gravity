# Gravity — Implementation Status

Last updated: 2026-10-03

## Current phase
Phase 05 — Activity Session Management

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
- Phase 03 - Authentication & Profile
- Phase 04 - Configurable Activity Engine
  - Created `ActivityType` and `ActivityMetric` models with strict constraints (slug uniqueness, only one primary metric, no negative configuration values).
  - Set up Django Admin with `ActivityMetricInline` for easy configuration.
  - Implemented `/api/activity-types/` (list active) and detail endpoint.
  - Wrote idempotent `seed_gravity` command and seeded Basketball, Running, Gaming, Studying, Workout, Soccer, Other.
  - Frontend `StartActivityScreen` now dynamically fetches and renders activities directly from the API.
  - Executed successful Pickleball acceptance test showing activity adds/removals work without code changes.
  - 9 backend tests written and passing; frontend TS checks and production build succeeded.

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
Begin Phase 05: Activity Session Management.
