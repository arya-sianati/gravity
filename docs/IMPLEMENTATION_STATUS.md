# Gravity — Implementation Status

Last updated: 2026-10-03

## Current phase
Phase 06 — Activity Sessions

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
- Phase 03 - Authentication & Profile
- Phase 04 - Configurable Activity Engine
- Phase 05 - Map Foundation
  - Clean `seed_gravity` to preserve admin modifications.
  - Installed `maplibre-gl` and built `GravityMap` and `MapControls` components.
  - Implemented safe Geolocation API with permissions handling and recenter UI.
  - Set up view bounding box tracking via `moveend` event for Phase 07 preparation.
  - Prepared empty heatmap sources and layers using dynamic Activity Types.
  - No WebSockets, Live Heat, or Session logic implemented (deferred to correct phases).
  - Production build and backend test checks pass.

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
Begin Phase 06: Activity Sessions.
