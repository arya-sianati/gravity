# Gravity — Implementation Status

Last updated: 2026-10-04

## Current phase
Phase 11 — Gravity XP & Levels

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
  - Built `MetricValue` model tracking integer/duration/boolean data uniquely per Participation and Metric.
  - Implemented dynamic UI form interpreting any activity's metric data types.
  - Form properly blocks finishing if required metrics are empty.
  - Auto-calculates exact duration metric upon explicit 'leave' action based on `joined_at`.
  - Added Leaderboard API serving ranks, values, handling stable ties, and period filtering (Today, Week, All-time).
  - Designed `LeaderboardScreen.tsx` dynamically supporting any custom metric unit.

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
Begin Phase 11: Gravity XP & Levels.
