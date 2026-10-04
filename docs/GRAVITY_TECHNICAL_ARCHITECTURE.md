# Gravity — Technical Architecture

## 1. Recommended Stack

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- MapLibre GL JS
- PWA support

### Backend
- Python
- Django
- Django REST Framework
- GeoDjango
- Django Channels

### Data / Infrastructure
- PostgreSQL
- PostGIS
- Redis
- Nginx
- ASGI application server
- Let's Encrypt / Certbot or equivalent TLS setup

### Admin
- Django Admin

### Development
- Git
- GitHub
- Antigravity

Before installation, verify current stable compatible package versions. Do not blindly pin versions from this document.

---

# 2. Why This Architecture

## Django
Provides:

- auth,
- ORM,
- Admin,
- API backend,
- permissions,
- migrations,
- mature ecosystem.

## PostGIS
Provides:

- geographic point storage,
- distance queries,
- bounding-box queries,
- clustering support,
- spatial indexes.

## Channels
Provides:

- realtime session/map updates over WebSockets.

## Redis
Provides:

- Channels communication layer,
- lightweight realtime infrastructure.

## MapLibre
Provides:

- interactive map,
- heatmap rendering,
- configurable map layers,
- open map rendering stack.

## Vite/React
Provides:

- fast SPA/PWA development,
- clean separation from Django backend,
- excellent mobile interactive UI workflow.

---

# 3. Runtime Topology

```text
Internet
   |
 HTTPS
   |
 Nginx
   |
   +------------------+
   |                  |
Frontend static    Django ASGI
files              /api /admin /ws
                      |
          +-----------+-----------+
          |                       |
     PostgreSQL/PostGIS        Redis
```

Possible route structure:

```text
/          frontend
/api/      REST API
/admin/    Django Admin
/ws/       WebSocket
/media/    media if later needed
/static/   Django/admin static
```

---

# 4. Django Apps

Recommended separation:

## `accounts`
- user model/profile
- privacy
- friendships

## `activities`
- ActivityType
- ActivityMetric
- ActivitySession
- Participation
- MetricValue
- map queries
- QR join

## `progression`
- XP
- levels
- badges
- streaks

## `events`
- GravityEvent
- Season
- event progress

## `challenges`
- FriendChallenge
- participants/results

## `pulse`
- Pulse Now
- recurring forecast/Pulse Soon

Avoid creating many tiny apps without need.

---

# 5. Custom User Model

Create a custom Django user model at project start.

Recommended fields beyond standard auth:

- display_name
- avatar later
- total_xp
- current_level
- location_privacy_mode
- created_at

Do not migrate to a custom user model late.

---

# 6. Spatial Fields

Use GeoDjango `PointField` for session anchor location.

Recommended:

- SRID 4326 storage.

Potential optional fields:

- last-known participant location should be treated carefully and stored only if needed.
- do not keep unnecessary high-resolution location history.

---

# 7. Map Query Strategy

Frontend sends visible bounding box:

- west,
- south,
- east,
- north.

Backend returns active sessions in viewport.

Filter:

- status active,
- recent enough,
- spatially inside viewport.

Response contains:

- session point,
- activity type,
- participant count,
- heat weight,
- privacy-safe details.

For small hackathon usage, session-level features are enough.

---

# 8. Heatmap Strategy

Prefer one MapLibre heatmap layer per activity type.

Heatmap source options:

### Option A — one GeoJSON source
All features contain activity slug; layers filter by slug.

### Option B — per-activity sources
Simpler dynamic layer management for some implementations.

Option A is likely cleaner for V1.

Each layer:

- filters to one activity,
- uses admin-provided color,
- uses `weight` property,
- uses zoom-adjusted radius/intensity,
- uses opacity so layers blend.

---

# 9. Dynamic Activity Colors

Frontend must retrieve Activity Type configuration from API.

Do not hard-code activity colors in multiple places.

Example API:

```json
{
  "slug": "basketball",
  "name": "Basketball",
  "icon": "🏀",
  "color": "#FF7A00"
}
```

Map layer builder consumes this configuration.

---

# 10. Session Participant Count

Maintain participant count by querying active Participation records.

For demo scale, aggregate query is acceptable.

If needed later:

- denormalized `active_participant_count`,
- signals/service update,
- cache.

Do not prematurely denormalize unless realtime performance requires it.

---

# 11. Realtime Flow

Example join:

1. Client POSTs join.
2. Backend validates user/session.
3. Participation becomes active.
4. Backend commits transaction.
5. Backend broadcasts event.
6. Connected clients update map/session details.

Important:
- broadcast after successful DB transaction,
- frontend should also refresh authoritative data periodically or after reconnect.

---

# 12. WebSocket Groups

Possible groups:

- `map_global` for hackathon simplicity,
- `map_geohash_*` later,
- `session_{id}`,
- `user_{id}`,
- `challenge_{id}`.

For a hackathon with limited users, start simple.

---

# 13. QR Join Implementation

Session receives random join token.

Example model field:

- UUID/random token
- unique
- unguessable

Frontend route:

`/join/{token}`

Flow:

1. open token route,
2. fetch session,
3. authenticate if required,
4. show session summary,
5. tap Join,
6. backend joins session.

Do not auto-join merely by opening the link if that could surprise the user.

---

# 14. Location Auto-Stop

Browser location tracking has platform limitations, especially when backgrounded.

Hackathon expectation:

- reliable while PWA/tab is active,
- best-effort when backgrounded.

Implementation:

1. frontend watches location during active participation when relevant;
2. sends periodic location heartbeat;
3. backend checks distance from session anchor;
4. if outside threshold, record outside_since;
5. if outside beyond grace period, mark participation ended;
6. frontend receives status update.

Do not promise native-background reliability from a web PWA.

---

# 15. Privacy-Safe Serialization

The API should not expose exact coordinates of individual private users by default.

Map primarily exposes aggregate/session heat.

For blurred personal activity:

- perturb/generalize display,
- use region/heat rather than named exact marker,
- do not serialize precise home point into public response.

---

# 16. Leaderboard Aggregation

Use database aggregation by:

- Activity Type,
- selected Metric,
- time range,
- Participation/MetricValue.

Period boundaries:

- Today
- Week
- Season
- All Time

Use timezone-aware datetime.

---

# 17. XP Service

Create a central backend service for XP awards.

Example reasons:

- PARTICIPATION_COMPLETED
- EVENT_COMPLETED
- STREAK
- BADGE
- CHALLENGE

Store XP ledger if feasible.

Recommended model:

`XPTransaction`

Fields:

- user,
- amount,
- reason,
- reference type/id,
- created_at.

Benefits:

- auditability,
- avoids mysterious XP changes,
- simplifies debugging.

---

# 18. Badge Service

Badge definition:

- name
- description
- icon
- active
- event link optional
- criteria type/config later

For hackathon, some badges may be awarded by direct service rules.

---

# 19. Season Scope

Store Season explicitly.

XPTransaction can optionally reference season.

Leaderboards can filter activity timestamp by Season bounds.

Do not duplicate all data per season.

---

# 20. Forecasting Architecture

P2.

Simplest approach:

1. bucket historical sessions geographically,
2. group by activity,
3. group by weekday,
4. group by time bucket,
5. require minimum observations,
6. calculate typical start time / participant range.

Could run:

- on request for demo,
- scheduled management command,
- periodic Celery job later.

Do not introduce Celery in V1 unless clearly needed.

---

# 21. Scheduled Jobs

Avoid Celery unless required.

For hackathon:

- management commands,
- cron/systemd timers,
- synchronous lightweight calculations.

Possible jobs:

- expire old sessions,
- recompute forecast cache,
- season transitions.

---

# 22. API Authentication

Choose one coherent model.

Recommended for same-domain deployment:

- Django session auth + CSRF can work well.

Alternative:
- DRF token/JWT, but adds token lifecycle complexity.

Because frontend and backend are served behind same domain, session cookies are attractive.

Do not add external auth services.

---

# 23. CORS

If frontend dev server runs separately during development, configure restricted dev CORS.

Production should ideally use same origin through Nginx.

This eliminates unnecessary cross-origin complexity.

---

# 24. Environment Variables

Example:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
REDIS_URL=
CSRF_TRUSTED_ORIGINS=
PUBLIC_BASE_URL=
```

Never commit secrets.

Provide `.env.example`.

---

# 25. Testing

Backend tests:

- activity creation
- join/leave
- QR token
- nearby session query
- metric validation
- leaderboard aggregation
- XP award
- privacy serialization
- event reward

Frontend tests/manual checks:

- map load
- activity start
- QR join
- realtime participant increment
- heatmap update
- denied location
- mobile responsiveness

---

# 26. Observability

Hackathon minimum:

- Django logs,
- Nginx logs,
- ASGI logs,
- structured exception logging if easy.

Do not spend significant time on external monitoring unless needed.

---

# 27. Seed Data

Provide command:

`python manage.py seed_gravity`

It should create initial Activity Types and sample metrics.

Example:

Basketball:
- points
- minutes

Running:
- distance_miles
- minutes

Gaming:
- wins
- minutes

Studying:
- minutes

Workout:
- minutes

Soccer:
- goals
- minutes

Other:
- minutes optional

Also create demo badges/event if requested by flag.

---

# 28. Demo Mode

Optional environment variable:

`GRAVITY_DEMO_MODE=true`

May allow:

- sample event creation,
- deterministic fake historical forecast data,
- seeded users/sessions.

Do not let demo shortcuts compromise production behavior.

---

# 29. Version Verification

Before implementation begins, Antigravity should verify:

- current stable Django release,
- current stable DRF,
- Channels compatibility,
- Python version compatibility,
- PostGIS compatibility,
- Node LTS,
- Vite compatibility,
- MapLibre version.

Use compatible stable versions rather than blindly using latest pre-release packages.
