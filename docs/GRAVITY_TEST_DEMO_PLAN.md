# Gravity — Test & Hackathon Demo Plan

# 1. Primary Demo Story

Use two phones or one phone + one second browser/device.

## Step A — Live map
Open Gravity and show the map.

Say:
> Gravity shows what people are actually doing around you right now.

## Step B — Start Basketball
Device A starts Basketball.

Expected:
- Basketball session created,
- live heat appears.

## Step C — QR
Device A shows QR.

Device B scans.

Expected:
- join page opens,
- B joins,
- participant count increases.

## Step D — Realtime heat
Expected:
- A updates without refresh,
- map heat becomes stronger.

## Step E — Metrics
B/A records Basketball points.

Expected:
- Basketball leaderboard changes.

## Step F — Multiple activities
Start Running or Gaming at another/nearby point.

Expected:
- second activity color appears,
- if overlapping, both remain visible.

## Step G — Pulse
Tap Pulse.

Expected:
- nearby activities ranked.

## Step H — Admin wow moment
Open Django Admin.

Either:
- activate Basketball Week,
or
- add Pickleball Activity Type.

Expected:
- public app reflects configuration without code change.

## Step I — Progress
Show:
- XP,
- level,
- badge/event reward,
- season.

---

# 2. Optional Forecast Demo

Seed repeated Basketball history.

Open Pulse Soon.

Show patterned predicted heat.

Explain:
> Gravity learns when activity repeatedly happens, so it can show not only what is happening now but what is likely to happen soon.

Only demo if stable.

---

# 3. Functional Test Matrix

## Authentication
- register
- login
- logout
- wrong password
- unauthorized mutation

## Activity configuration
- admin creates activity
- activity appears frontend
- admin edits color
- heat layer uses new color
- metric config appears in form

## Sessions
- start
- join
- leave
- creator leaves while others remain
- last participant leaves

## QR
- valid token
- ended-session token
- invalid token
- unauthenticated scan then login

## Map
- one activity
- multiple nearby same activities
- distant same activities
- overlapping different activities
- pan/zoom
- denied location

## Realtime
- join
- leave
- metric update if broadcast
- reconnect

## Metrics
- valid
- negative invalid if configured
- wrong activity metric rejected
- leaderboard correct

## XP
- participation reward
- duplicate finish does not double reward
- event reward once

## Privacy
- Hidden
- Blurred
- Friends
- Exact
- non-friend cannot access friend-only exact location

## Events
- inactive event
- active event
- qualification
- reward
- expiration

## Seasons
- active season
- date boundaries
- season leaderboard

## Friends
- request
- accept
- reject
- remove

## Challenges
- create
- accept
- progress
- finish

## Auto-stop
- inside radius
- outside grace
- return during grace
- leave beyond grace
- disabled activity unaffected

---

# 4. Mobile Device Checklist

On actual phone:

- HTTPS loads
- map loads
- GPS permission
- camera permission
- QR scans
- bottom navigation usable
- no horizontal overflow
- keyboard does not destroy forms
- active-session controls reachable
- PWA install if implemented

---

# 5. Failure Fallbacks

If WebSocket fails during judging:
- frontend should refresh map/session through REST after action.

If location is flaky:
- provide a demo-only manual coordinate override guarded behind demo mode or use seeded location.

If few real users:
- seed demo sessions to make heatmap visually meaningful.

If forecast lacks enough history:
- seed clearly labeled demo history before presentation.

Do not fake a feature while claiming it is real. Seeded demo data is fine if described as seeded/historical demo data.

---

# 6. Presentation Timing

Suggested 3-minute structure:

### 0:00–0:25
Problem + concept.

### 0:25–1:35
Live map → start activity → QR → realtime heat.

### 1:35–2:05
Leaderboard + XP/event.

### 2:05–2:30
Admin adds/configures an activity.

### 2:30–2:50
Pulse / optional forecast.

### 2:50–3:00
Vision:
> Social media shows what people post. Gravity shows what people are actually doing.

---

# 7. Pre-Demo Checklist

- commit known-good code,
- DB backup,
- server restarted,
- TLS valid,
- Redis running,
- Postgres running,
- ASGI running,
- Nginx running,
- admin login ready,
- two users logged in,
- camera works,
- GPS works,
- QR tested,
- event seeded,
- leaderboard seeded enough to look meaningful,
- no browser console errors,
- no pending destructive migrations.

---

# 8. Judging Talking Points

Technical depth:
- PostGIS geospatial queries,
- live WebSockets,
- dynamic Activity Type engine,
- configurable metrics,
- heatmap visualization,
- privacy-aware location,
- self-hosted Django stack.

Product differentiation:
- live activity instead of static posts,
- overlapping activity gravity instead of territory ownership,
- easy QR participation,
- different activity metrics,
- map history/forecast potential,
- admin can launch new categories/events rapidly.

Theme:
- Gravity connects people through what is happening around them in real space, in real time.
