# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 22 — Production Deployment (Complete)

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
- Phase 17 - Friend Challenges
  - Database models `FriendChallenge`, `ChallengeParticipant`, and `ChallengeReward` with unique constraints, validation, and migration `0008`.
  - Comprehensive service layer supporting all 3 challenge types: `first_to_target` (first to reach target value wins, completion timestamp tie-breaker), `highest_by_deadline` (highest metric value at deadline wins; co-winners with competition ranking `1, 1, 3`), and `cooperative_target` (sum of accepted participants >= target).
  - Configurable `ActivityMetric` architecture reuse with dynamic metric validation across standard and dynamic activities (e.g. Pickleball).
  - Strict privacy and authorization isolation: challenges are strictly between accepted friends, non-accepted users cannot view or participate, and challenge participation never exposes or bypasses location privacy.
  - Idempotent, database-backed XP distribution via `ChallengeReward` unique constraints (Participation XP + Winner XP) integrated with `XPTransaction`.
  - Realtime challenge notifications via Channels consumer `GravityChallengeConsumer` routed at `/ws/gravity/challenge/<id>/`.
  - Frontend TypeScript API client `frontend/src/api/challenges.ts` and interactive UI in `FriendsScreen.tsx` (Challenges tab, filter chips, challenge creator modal, progress bars, winner badges, invitation accept/decline/cancel actions).
  - Dedicated test suite `activities/tests_phase17.py` (16 comprehensive tests; 136 tests passing repository-wide).
- Phase 18 - Auto-Stop & Session Integrity
  - Configurable `auto_stop_mode` (`disabled`, `anchor_radius`, `inactivity`) and validation on `ActivityType`, distinguishing stationary-area activities from movement activities (e.g. Basketball vs Running).
  - PostGIS spherical anchor radius calculations comparing participant coordinates against exact session anchor (`Distance('location', point)`).
  - Heartbeat tracking fields on `Participation`: `last_heartbeat_at`, `outside_since`, and `last_location` without storing a permanent GPS trail or leaking coordinates.
  - Grace period state machine: inside resets `outside_since`; outside begins grace timer; continued outside >= `auto_stop_grace_seconds` triggers auto-stop; returns inside resets grace. Support for zero grace.
  - Authoritative, unified lifecycle service `finalize_participation` shared between manual leave and auto-stop with row-locking concurrency protection (`select_for_update`) and idempotent XP/streak/badge/event/challenge evaluations.
  - Dedicated endpoints `POST /api/me/activity-location/` and `POST /api/participations/<id>/heartbeat/` returning privacy-safe state.
  - Django Admin integration with auto-stop controls and updated seed defaults across activities.
  - Frontend periodic heartbeat (25s interval), `visibilitychange` listener, grace warning banner in `ActiveActivityScreen.tsx`, and auto-stop feedback toast in `AppShell.tsx`.
  - Dedicated test suite `activities/tests_phase18.py` (17 comprehensive tests; 153 tests passing repository-wide).
- Phase 19 - Gravity History / Area Reputation
  - PostGIS spherical spatial history queries (`Distance('location', point) <= radius_m`) around arbitrary coordinates without requiring named venues, campuses, or predefined boundaries.
  - Factual aggregate calculation: total sessions, total qualifying participations, and unique participants across qualifying sessions (`status == ENDED`, non-cancelled, duration >= 60s).
  - Dominant activity determination based on qualifying participation volume with session count as tie-breaker.
  - Activity breakdown: participation counts, session counts, unique participants, and share percentage per active activity type.
  - Temporal patterns: 24-hour distribution across eight 3-hour buckets identifying peak time, and 7-day weekday distribution identifying busiest day in application timezone.
  - Privacy safeguard & small-number suppression: configurable `GRAVITY_HISTORY_MIN_PARTICIPANTS` (default: 3) suppressing breakdown when unique participant count is low to protect individual routines from deanonymization. Zero exposure of user IDs, usernames, or raw coordinates.
  - RESTful endpoints `GET /api/history/area/` and `GET /api/map/history/` with flexible period filtering (`today`, `7d`, `30d`, `90d`, `season`, `all`) and radius controls.
  - Dynamic ActivityType support automatically functioning for custom activities (e.g. Pickleball) with color, icon, and name styling.
  - Frontend TypeScript client `frontend/src/api/history.ts`, interactive `AreaHistoryModal.tsx` inspection sheet with period chips, radius selector, dominant activity banner, share bars, and pattern summaries, integrated directly into `GravityMap.tsx` (map clicks and controls) and `PulseScreen.tsx`.
  - Dedicated automated test suite `activities/tests_phase19.py` (14 comprehensive tests; 167 tests passing repository-wide).
- Phase 20 - Pulse Soon / Historical Forecasting
  - Near-term recurring activity forecasting engine in `forecast_service.py` using explainable, deterministic statistical heuristics (recurrence across weeks, day-of-week matching, 2-hour diurnal windows, volume, recency decay, and proximity) with zero black-box AI.
  - Spatial grouping into coarse geographic cells (~350m grid via `snap_to_grid`) generating 16-point circular polygon GeoJSON geometries; never exposes raw coordinates or user identities.
  - Dual privacy anonymity gates: strictly requires both `unique_users >= GRAVITY_HISTORY_MIN_PARTICIPANTS` (3) and `distinct_weeks >= GRAVITY_FORECAST_MIN_OCCURRENCES` (3) to suppress single-user or one-time routines.
  - Live duplicate suppression: automatically detects active sessions matching activity type and cell, omitting redundant "Soon" predictions.
  - RESTful endpoint `GET /api/pulse/soon/` with full validation of `lat`, `lng`, `radius`, `horizon_minutes`, `activity`, and `limit`.
  - Frontend Pulse screen segmented control (`Pulse Now` / `Pulse Soon`) with confidence pills (Very strong / Strong / Moderate pattern), pattern explanation reasons, historical evidence metrics, and Gravity Event XP bonus integration.
  - Frontend MapLibre overlay: distinct translucent fill (`pulse-soon-fill`) and patterned dashed outline (`pulse-soon-outline`) with interactive inspection popups and a forecast toggle control.
  - Dedicated automated test suite in `activities/tests_phase20.py` (18 comprehensive tests; 185 tests passing repository-wide).
- Phase 21 - PWA / Mobile Polish
  - Full PWA installability configured via `vite-plugin-pwa` with web manifest (name: Gravity, theme `#030712`, background `#000000`, display: standalone, portrait orientation, icons 192x192, 512x512, 512x512 maskable).
  - Conservative Workbox caching: app shell and static assets precached; network-authoritative live data for `/api/`, `/ws/`, and `/admin/`.
  - Offline/degraded experience with global offline banner and automatic state recovery on reconnect.
  - Native PWA update prompt notifying users when a new service worker is installed with "Refresh" action invoking `SKIP_WAITING`.
  - Mobile safe areas and dynamic viewport handling: `env(safe-area-inset-top/bottom)`, `100dvh`, `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation`, `.pt-safe`, `.pb-safe`, and `prefers-reduced-motion`.
  - Bottom navigation polish with 5 primary surfaces (Map, Pulse, Friends, Rank, Profile) and $\ge 44\times 44$px touch targets.
  - Route-level lazy loading (`React.lazy` + `Suspense`), reducing the initial application bundle from 1.48MB to 265kB.
  - Touch targets and mobile form handling: `inputMode="numeric"`/`"decimal"`, responsive QR code scaling, and "Copy Join Link" clipboard action.
  - Standardized location UX with user-friendly error formatting and educational privacy copy.
- Phase 22 - Production Deployment
  - Canonical domain `https://gravity.college` deployed with 301 permanent redirect from `https://www.gravity.college` preserving paths and query strings.
  - Port 80 HTTP-to-HTTPS redirect for all traffic.
  - Production TLS provisioned via Let's Encrypt / Certbot (`gravity.college` + `www.gravity.college`) with automated background renewal timer (`certbot.timer`).
  - Production Nginx reverse proxy routing: React PWA (`/`), Django REST API (`/api/`), Django Admin (`/admin/`), Django static assets (`/static/`), and WebSockets (`/ws/`).
  - ASGI application daemonized via systemd (`gravity.service`) running Daphne on localhost port 8000 with restart-on-failure and automated boot enablement.
  - Verified server restart-persistence: PostgreSQL 15, Redis 7, Nginx 1.22, and Daphne ASGI (`gravity.service`) all automatically resumed after unexpected server reboot.
  - Database role security maintained: `gravity_user` operates under least privilege without PostgreSQL SUPERUSER role.
  - Secure production environment (`backend/.env`, mode `0600`) with strong random `SECRET_KEY`, `DEBUG=False`, `PUBLIC_BASE_URL=https://gravity.college`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `X-Frame-Options=DENY`, and `nosniff`.
  - Production WebSocket handshake verified over TLS (`wss://gravity.college/ws/gravity/`) with `AllowedHostsOriginValidator` and Redis channel layer.
  - Comprehensive two-client smoke test passing across session creation, QR join URL generation (`https://gravity.college/join/<token>`), unauthenticated preview, QR join, real-time participant updates, heartbeat tracking, and session leaves.
  - Automated deployment helper script created at `scripts/deploy.sh` and full operations guide documented in `docs/GRAVITY_DEPLOYMENT.md`.

## Next phase
- Phase 23 — Demo Hardening & Final Acceptance

## In progress
- None

## Known issues
- Physical second-phone camera QR scanning requires physical mobile device verification.

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
Begin Phase 23: Demo Hardening & Final Acceptance.
