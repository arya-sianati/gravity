# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 09 — WebSockets Foundation

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation (Includes Security Fix)
- Phase 02 - Frontend Foundation
- Phase 03 - Authentication & Profile
- Phase 04 - Configurable Activity Engine
- Phase 05 - Map Foundation
- Phase 06 - Activity Sessions
- Phase 07 - Live Map Heat
  - Built GeoDjango bounding box queries.
  - Implemented exact, blurred (500m deterministic grid), and hidden privacy coordinates securely.
  - Deployed dynamic MapLibre heatmap layers driven by backend Activity Type configurations.
  - Comprehensive PostGIS test coverage.
- Phase 08 - QR Joining
  - Designed opaque `UUID4` token architecture.
  - Built `GET /api/join/{token}/` preview endpoint (privacy-safe).
  - Built `POST /api/join/{token}/` secure join execution endpoint.
  - Installed `qrcode.react` to render codes locally on the `ActiveActivityScreen`.
  - Configured `ProtectedRoute` routing in `App.tsx` matching intended authentication flow safely returning to the QR URL after login.

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
Begin Phase 09: WebSockets Foundation.
