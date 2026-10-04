# Gravity — Full Build Phases

The phases are ordered to preserve a working product at all times.

Do not start a later phase because it looks exciting while an earlier required phase is broken.

---

# Phase 00 — Repository & Specification Lock

## Goal
Establish a clean repository and source of truth.

## Tasks
- Create repository.
- Add specification docs.
- Create `.gitignore`.
- Create `.env.example`.
- Add root README.
- Decide backend/frontend directories.
- Record installation commands.
- Create `IMPLEMENTATION_STATUS.md`.

## Exit criteria
- repository builds as an empty scaffold,
- agent has read specification,
- no legacy/unrelated project code.

---

# Phase 01 — Backend Foundation

## Goal
Create stable Django foundation.

## Tasks
- Create virtual environment.
- Install verified compatible stable Django stack.
- Create Django project.
- Create custom User model immediately.
- Configure environment variables.
- Configure PostgreSQL.
- Enable PostGIS.
- Configure GeoDjango.
- Run initial migrations.
- Create superuser.
- Verify Django Admin.

## Exit criteria
- Django runs,
- database works,
- PostGIS works,
- admin login works,
- clean migration succeeds.

---

# Phase 02 — Frontend Foundation

## Goal
Create mobile-first React application.

## Tasks
- Create Vite React TypeScript project.
- Add Tailwind.
- Add routing.
- Add API client wrapper.
- Add environment config.
- Add basic mobile layout.
- Create placeholder screens:
  - Map
  - Pulse
  - Friends
  - Profile
  - Start Activity

## Exit criteria
- frontend builds,
- mobile layout works,
- frontend can call Django health endpoint.

---

# Phase 03 — Authentication & Profile

## Goal
Allow real users.

## Backend
- registration
- login
- logout
- current user endpoint
- session/CSRF configuration
- basic profile
- privacy enum

## Frontend
- login/register screen
- auth state
- logout
- profile basics

## Exit criteria
- two independent users can register/login,
- auth survives normal page reload,
- unauthorized mutations rejected.

---

# Phase 04 — Configurable Activity Engine

## Goal
Make activities data-driven.

## Backend
Implement:

- ActivityType
- ActivityMetric
- Django Admin
- API list/detail
- seed command

Seed:

- Basketball
- Running
- Gaming
- Studying
- Workout
- Soccer
- Other

Seed metrics.

## Frontend
- fetch activity types dynamically
- render icons/names/colors
- activity selection UI

## Exit criteria
- admin can add a new Activity Type,
- frontend shows it without code change,
- metrics are editable through admin.

### Demo checkpoint
Create Pickleball through Admin and verify it appears.

---

# Phase 05 — Map Foundation

## Goal
Render real map.

## Tasks
- Add MapLibre.
- Request geolocation.
- Handle denied permission.
- Center/recenter control.
- mobile map layout.
- empty activity layer framework.
- map viewport/bounding-box state.

## Exit criteria
- map works on phone and desktop,
- location denial does not break app,
- frontend can report visible bbox.

---

# Phase 06 — Activity Sessions

## Goal
Start and end live activity.

## Backend
- ActivitySession
- Participation
- create session endpoint
- join/leave
- active participation query
- permissions

## Frontend
- Start Activity flow
- Active Activity screen
- elapsed timer
- participant count
- leave/end

## Exit criteria
- user can start Basketball,
- session appears in database,
- user is active participant,
- user can leave,
- session lifecycle behaves correctly.

---

# Phase 07 — Live Map Heat

## Goal
Activity changes the map.

## Backend
- GeoJSON/live map endpoint
- bbox filtering
- participant counts
- heat weight
- privacy-safe payload

## Frontend
- create heatmap layer per Activity Type
- dynamic colors
- dynamic weights
- refresh map data
- activity filters

## Exit criteria
- one active user produces visible Basketball heat,
- more participants increase intensity,
- separate distant activity appears separately,
- nearby session heat overlaps naturally.

---

# Phase 08 — QR Join

## Goal
Make joining frictionless.

## Backend
- secure join token
- token resolver
- join endpoint

## Frontend
- QR generation
- `/join/:token` route
- session preview
- Join confirmation

## Exit criteria
- Device A starts activity.
- Device B scans QR.
- B joins correct session.
- participant count updates.

---

# Phase 09 — Realtime WebSockets

## Goal
No manual refresh.

## Backend
- Django Channels
- Redis
- WebSocket routing
- session/map events

## Frontend
- WebSocket client
- reconnect
- update current session
- refresh/update map features

## Exit criteria
- QR join on Device B changes Device A participant count quickly,
- map heat changes on connected clients,
- reconnect recovers after temporary disconnect.

---

# Phase 10 — Metrics & Activity Leaderboards

## Goal
Make activity competition meaningful.

## Backend
- MetricValue
- metric update endpoint
- validation
- period filters
- leaderboard aggregation

Periods:
- Today
- Week
- Season when available
- All Time

## Frontend
- metric entry
- leaderboard
- period tabs

## Exit criteria
- Basketball points rank Basketball users,
- Running distance ranks Running users,
- metrics are not hard-coded in frontend.

---

# Phase 11 — Personal XP & Levels

## Goal
Create cross-activity progression.

## Backend
- XPTransaction
- XP award service
- level calculation
- participation completion XP

## Frontend
- XP display
- level display
- progress bar

## Exit criteria
- completing qualifying participation awards XP once,
- duplicate API calls do not double-award incorrectly,
- level updates correctly.

---

# Phase 12 — Badges & Consistency

## Goal
Create visible achievements.

## Backend
- Badge
- UserBadge
- daily streak
- award service

## Frontend
- badges on profile
- streak display
- earned-badge feedback

## Exit criteria
- seeded badge can be earned,
- streak updates predictably,
- badge persists.

---

# Phase 13 — Gravity Events

## Goal
Allow platform-created special events.

## Backend
- GravityEvent
- admin
- active-event lookup
- reward calculation
- badge/XP reward

## Frontend
- event card/banner
- event status inside activity
- progress/completion

## Exit criteria
- admin can launch Basketball Week,
- users participating in Basketball see it,
- qualifying user receives configured reward.

---

# Phase 14 — Seasons

## Goal
Introduce recurring competitive eras.

## Backend
- Season
- active season resolver
- season-aware leaderboard
- season XP attribution

## Frontend
- current season indicator
- season profile section
- season leaderboard filter

## Exit criteria
- one active season,
- current activity can be ranked within season,
- historical data remains after season change test.

---

# Phase 15 — Pulse Now

## Goal
Make discovery easy.

## Backend
- nearby activity ranking
- proximity
- participant strength
- optional event boost

## Frontend
- central Pulse button
- Pulse Now sheet/page
- activity cards
- tap to map/join

## Exit criteria
- Pulse shows nearby active activities in useful order,
- selecting result navigates correctly.

---

# Phase 16 — Friends

## Goal
Add social connection.

## Backend
- Friendship
- request/accept
- friend list
- privacy checks
- lightweight friend activity data

## Frontend
- add friend
- requests
- friend list
- friend activity
- privacy setting UI

## Exit criteria
- users can become friends,
- friends can view allowed activity/progression,
- non-friends cannot access friends-only location details.

---

# Phase 17 — Friend Challenges

## Goal
Add direct competition/cooperation.

## Backend
- FriendChallenge
- ChallengeParticipant
- challenge modes
- progress calculation
- result finalization

## Frontend
- create challenge
- accept
- progress
- result

## Exit criteria
- two users can complete one real challenge flow.

---

# Phase 18 — Auto-Stop

## Goal
Reduce forgotten live activities.

## Backend
- location heartbeat endpoint
- distance check
- outside_since
- grace period
- auto-stop transition

## Frontend
- location watch for enabled activities
- heartbeat
- "Still active?" warning if appropriate
- stopped state handling

## Exit criteria
- Basketball participant leaving configured radius auto-stops after grace period,
- Running is unaffected when configured differently.

Note:
PWA background tracking limitations must be documented.

---

# Phase 19 — Gravity History

## Goal
Give places reputation without named territories.

## Backend
- history around point/radius
- period aggregation
- top Activity Types
- peak/typical activity

## Frontend
- tap/long-press area history
- Today/Week/Season tabs

## Exit criteria
- a geographic point can show historical top activity.

---

# Phase 20 — Pulse Soon / Forecast

## Goal
Predict recurring activity.

## Backend
- historical clustering
- weekday/time buckets
- minimum observation threshold
- forecast confidence

## Frontend
- Pulse Soon
- predicted activity card
- hatched/patterned map overlay

## Exit criteria
- seeded or real repeated Basketball sessions generate a forecast,
- forecast is visually distinct from live heat.

P2. Cut first if time is limited.

---

# Phase 21 — PWA Polish

## Goal
Make demo feel like an app.

## Tasks
- manifest
- icons
- installability
- splash/meta tags
- mobile safe areas
- loading states
- error states

## Exit criteria
- installable on supported device/browser,
- app opens cleanly from home screen.

---

# Phase 22 — Production Deployment

## Goal
Make Gravity publicly reachable.

## Tasks
- server packages
- PostgreSQL/PostGIS
- Redis
- backend environment
- frontend production build
- ASGI service
- Nginx
- TLS certificate
- DNS
- static files
- migrations
- superuser
- seed command

## Exit criteria
- HTTPS domain works,
- WebSockets use `wss`,
- Admin works securely,
- QR link resolves on second phone,
- location/camera work over HTTPS.

---

# Phase 23 — Demo Hardening

## Goal
Protect presentation.

## Tasks
- seed demo users
- seed sample history
- seed active event
- ensure two-device flow
- create fallback demo data
- test poor network reconnect
- test fresh browser
- test QR
- test mobile permissions
- rehearse admin configuration wow moment

## Exit criteria
Complete demo succeeds twice in a row from clean start.

---

# Final Priority Buckets

## P0
Phases 00–10 plus deployment basics.

## P1
Phases 11–17 and 21–23.

## P2
Phases 18–20 and richer polish.

If hackathon time is tight:

1. Finish P0.
2. Deploy.
3. Add P1 selectively.
4. Only then attempt P2.
