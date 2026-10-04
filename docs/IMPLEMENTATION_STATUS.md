# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 16 — Friends & Privacy (Complete)

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
- Phase 13 - Gravity Events
- Phase 14 - Seasons
- Phase 15 - Pulse Now
- Phase 16 - Friends & Privacy
  - Canonical `Friendship` model with database-level ordering (`user_a.id < user_b.id`), pair uniqueness, and self-friending check constraints.
  - Authoritative, unified privacy resolver `resolve_location_visibility` governing Map (GeoJSON coordinates), Pulse (session inclusion and distance format), Session Detail, and Friends Presence.
  - Safe User Search endpoint `GET /api/users/search/?q=...` returning only public safe fields (id, username, display_name, current_level, friendship_status), strictly omitting email, coordinates, or passwords, and excluding the requesting user.
  - Public Profile endpoint `GET /api/users/<id>/profile/` with badges, streak, friendship status, and privacy-governed active session context.
  - Friend request lifecycle (`/api/friends/request/`, incoming, outgoing, accept, decline, cancel, remove) with automatic reciprocal acceptance and idempotent request handling.
  - Friends list and Live Presence endpoint `GET /api/friends/presence/` surfacing active friend sessions with privacy-safe coarse or exact distance presentation.
  - Interactive Location Privacy Settings selector in `ProfileScreen.tsx` with live `PATCH /api/me/` updates supporting Hidden, Blurred (~500m grid default), Friends Only, and Exact modes.
  - Frontend `FriendsScreen.tsx` featuring a 3-tab layout (`Friends` with live presence feed and roster, `Requests` with incoming/outgoing actions, `Find Friends` with real-time search), and a user profile inspection modal.
  - Dedicated automated test suite in `accounts/tests_phase16.py` (14 comprehensive tests; 120 tests passing repository-wide).

## In progress
- None

## Known issues
- Phone-camera QR testing recorded as pending for deployment/demo hardening.

## Deferred
- None

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
Begin Phase 17: Challenges.
