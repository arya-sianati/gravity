# Gravity — Implementation Status

Last updated: 2026-10-03

## Current phase
Phase 03 — Users & Profiles

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
  - Installed Node.js LTS (v24.21.0).
  - Initialized React + TypeScript + Vite (`frontend` app).
  - Configured Tailwind CSS v4.
  - Added React Router with AppShell layout.
  - Created placeholder screens (`MapScreen`, `PulseScreen`, `FriendsScreen`, `ProfileScreen`, `StartActivityScreen`).
  - Created API client with Axios (`apiClient`).
  - Configured proxy for `/api` and `/ws` to Django backend.
  - Implemented `/api/health/` backend endpoint.
  - Frontend successfully fetches from health endpoint.

## In progress
- None

## Known issues
- None

## Deferred
- See `GRAVITY_BUILD_PHASES.md`.

## Setup / migration commands
```bash
# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate

# Setup frontend
cd frontend
npm install
npm run dev
```

## Next recommended task
Begin Phase 03: Profile Setup & Auth.
