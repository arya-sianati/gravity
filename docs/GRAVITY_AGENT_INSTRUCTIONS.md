# Gravity — Instructions for Antigravity / Coding Agents

## 1. Source of truth

Before changing code, read:

- `GRAVITY_MASTER_SPEC.md`
- `GRAVITY_PRODUCT_DECISIONS.md`
- `GRAVITY_TECHNICAL_ARCHITECTURE.md`
- `GRAVITY_DATA_MODEL.md`
- `GRAVITY_BUILD_PHASES.md`

Treat these files as authoritative.

Do not reintroduce ideas that were intentionally removed.

Do not convert Gravity into a generic social network, generic event app, generic fitness tracker, or generic marketplace.

## 2. Product principle

Gravity's core loop is:

1. User opens the live map.
2. User sees real activity happening nearby.
3. User starts or joins an activity.
4. Their participation contributes to the live map heat.
5. They earn personal progress and activity-specific stats.
6. They can compare with friends and activity leaderboards.
7. They return because the real world around them changes, events rotate, seasons progress, friends are active, and nearby activity is visible.

## 3. Engineering principles

- Prefer the simplest implementation that supports the agreed product.
- Do not create unnecessary microservices.
- Keep frontend and backend separated cleanly.
- Use Django as the backend authority.
- Use Django Admin instead of building a custom admin frontend for V1.
- Use PostgreSQL with PostGIS for geospatial data.
- Use WebSockets for live map/session updates.
- Use Redis only as infrastructure for realtime/channel coordination if needed.
- Keep activity behavior data-driven and configurable.
- Do not hard-code basketball, running, gaming, studying, workout, or soccer logic into unrelated parts of the codebase.
- Activity-specific behavior should be controlled by database configuration wherever practical.
- Self-reporting is valid and should not be treated as suspicious by default.
- Privacy defaults must be conservative for home/private-location activity.
- Do not expose exact residential coordinates unless the user explicitly allows exact location sharing.

## 4. Hackathon priorities

### P0 — required
- authentication
- user profile
- map
- configurable activity types
- start activity
- join activity
- QR join
- leave/end activity
- live heatmap
- live participant count
- activity metrics
- basic leaderboard
- Django Admin
- deployment over HTTPS

### P1 — high-value
- personal Gravity XP/level
- badges
- Gravity Events
- seasons
- Pulse
- friends
- friend activity
- friend challenges
- privacy modes
- location-based auto-stop
- activity history

### P2 — only after P0/P1 are stable
- Pulse Soon / recurring activity forecasting
- richer seasonal history
- advanced verification weighting
- feed/photos
- advanced anti-cheat
- community creation
- venue/area hierarchy
- sophisticated recommendations

## 5. Behavior when requirements are ambiguous

When ambiguity exists:

1. choose the simplest behavior that preserves the product idea;
2. keep the code extensible;
3. document the assumption;
4. do not block implementation for non-critical ambiguity.

## 6. Testing expectations

For every phase:

- run backend tests;
- run frontend type-check/build;
- test migrations from a clean database;
- test at least one happy-path flow;
- verify mobile layout;
- verify location permission failure behavior;
- verify WebSocket reconnect behavior when relevant.

For map/session phases, test with at least two browser sessions to confirm realtime updates.

## 7. Demo protection

Never sacrifice a working demo for a large refactor late in the hackathon.

If time becomes limited:

- freeze architecture,
- cut P2,
- then cut P1,
- preserve the complete P0 user flow.

## 8. Deliverable discipline

After completing a phase, update a short `IMPLEMENTATION_STATUS.md` containing:

- completed items,
- known issues,
- deferred items,
- migration/setup commands,
- next recommended phase.

Do not silently change the specification.
