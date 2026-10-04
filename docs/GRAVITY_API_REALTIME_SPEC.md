# Gravity — API & Realtime Contract Guidance

This is an implementation contract draft. Small naming changes are allowed if kept consistent.

# 1. Conventions

- JSON REST API.
- Authenticated mutation endpoints.
- UTC timestamps in API.
- UUIDs preferred for externally exposed session identifiers.
- Never expose exact private user coordinates unless authorized.
- Errors should use a consistent structure.

Suggested error:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Metric value is invalid.",
    "fields": {
      "points": ["Must be 0 or greater."]
    }
  }
}
```

---

# 2. Activity Types

## GET `/api/activity-types/`

Response:

```json
[
  {
    "id": 1,
    "name": "Basketball",
    "slug": "basketball",
    "icon": "🏀",
    "color": "#...",
    "cluster_radius_m": 200,
    "qr_join_enabled": true,
    "self_start_enabled": true,
    "metrics": [
      {
        "id": 1,
        "name": "Points",
        "slug": "points",
        "unit": "pts",
        "data_type": "integer",
        "is_primary": true,
        "leaderboard_enabled": true
      }
    ]
  }
]
```

---

# 3. Start Session

## POST `/api/sessions/`

Request:

```json
{
  "activity_type": "basketball",
  "latitude": 38.0,
  "longitude": -93.0,
  "privacy_mode": "blurred"
}
```

Response:

```json
{
  "id": "uuid",
  "activity_type": "basketball",
  "status": "active",
  "started_at": "...",
  "participant_count": 1,
  "my_participation_id": 123
}
```

---

# 4. Join Suggestion

Before creating a session, frontend may call:

## GET `/api/sessions/nearby/?activity=basketball&lat=...&lng=...`

Return likely join candidates within Activity Type configured radius.

---

# 5. Session Detail

## GET `/api/sessions/{id}/`

Return:

- Activity Type,
- status,
- approximate map info,
- participant count,
- current user's participation state,
- metrics configuration,
- event bonuses.

Do not list private participant locations.

---

# 6. Join

## POST `/api/sessions/{id}/join/`

Optional request:

```json
{
  "join_method": "map"
}
```

Server should infer/validate method when possible rather than trusting arbitrary client claims.

---

# 7. Leave

## POST `/api/sessions/{id}/leave/`

May accept final metrics.

```json
{
  "metrics": {
    "points": 17
  }
}
```

---

# 8. Metrics

## PATCH `/api/participations/{id}/metrics/`

```json
{
  "points": 17
}
```

Backend maps slugs to configured ActivityMetric.

Reject metrics that do not belong to session Activity Type.

---

# 9. QR

## GET `/api/sessions/{id}/join-code/`

Return:

```json
{
  "join_url": "https://gravity.example.com/join/<opaque-token>",
  "expires_at": null
}
```

Frontend generates QR locally.

## GET `/api/join/{token}/`

Returns privacy-safe session preview.

## POST `/api/join/{token}/`

Joins authenticated user.

---

# 10. Live Map

## GET `/api/map/live/?bbox=west,south,east,north`

Response GeoJSON:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-93.0, 38.0]
      },
      "properties": {
        "session_id": "uuid",
        "activity_slug": "basketball",
        "participant_count": 8,
        "weight": 8
      }
    }
  ]
}
```

Exact session point must be privacy-safe.

If private home activity should not expose anchor, backend may return generalized/shifted point or aggregate feature.

---

# 11. Hotspot Detail

Possible endpoint:

## GET `/api/map/summary/?lat=...&lng=...&radius=...`

Response:

```json
{
  "activities": [
    {
      "activity_slug": "basketball",
      "active_count": 24,
      "gravity_strength": 91
    },
    {
      "activity_slug": "running",
      "active_count": 9,
      "gravity_strength": 52
    }
  ]
}
```

---

# 12. Leaderboards

## GET `/api/leaderboards/basketball/?period=week`

Response:

```json
{
  "activity": "basketball",
  "metric": "points",
  "period": "week",
  "rows": [
    {
      "rank": 1,
      "user": {
        "id": 1,
        "display_name": "Maya"
      },
      "value": 184
    }
  ],
  "me": {
    "rank": 14,
    "value": 92
  }
}
```

---

# 13. XP / Profile

## GET `/api/me/profile/`

Return:

- total XP,
- level,
- next-level progress,
- streak,
- badges,
- season summary,
- activity tenure/stats.

---

# 14. Gravity Events

## GET `/api/events/active/`

Return currently published events.

Backend decides reward eligibility.

Do not allow frontend to award itself XP.

---

# 15. Seasons

## GET `/api/seasons/current/`

Return season dates + current user's summary.

---

# 16. Pulse Now

## GET `/api/pulse/now/?lat=...&lng=...`

Response:

```json
{
  "results": [
    {
      "activity_slug": "basketball",
      "distance_m": 480,
      "active_count": 24,
      "gravity_strength": 91,
      "event": null
    }
  ]
}
```

---

# 17. Pulse Soon

P2.

## GET `/api/pulse/soon/?lat=...&lng=...`

Response:

```json
{
  "results": [
    {
      "activity_slug": "basketball",
      "center": {
        "lat": 38.0,
        "lng": -93.0
      },
      "radius_m": 250,
      "expected_start": "...",
      "typical_participants_min": 12,
      "typical_participants_max": 18,
      "confidence": 0.82
    }
  ]
}
```

---

# 18. Friends

Suggested endpoints:

```text
GET    /api/friends/
GET    /api/friends/requests/
POST   /api/friends/requests/
POST   /api/friends/requests/{id}/accept/
POST   /api/friends/requests/{id}/reject/
DELETE /api/friends/{id}/
```

---

# 19. Challenges

```text
GET  /api/challenges/
POST /api/challenges/
POST /api/challenges/{id}/accept/
POST /api/challenges/{id}/decline/
GET  /api/challenges/{id}/
```

Backend computes results from metric records.

---

# 20. Location Heartbeat

Only for activity types requiring it.

## POST `/api/participations/{id}/location-heartbeat/`

```json
{
  "latitude": 38.0,
  "longitude": -93.0,
  "accuracy_m": 15,
  "recorded_at": "..."
}
```

Backend should not retain more location history than necessary.

Response may include:

```json
{
  "state": "inside"
}
```

or:

```json
{
  "state": "outside_grace",
  "grace_remaining_seconds": 180
}
```

---

# 21. WebSocket

Suggested endpoint:

`wss://gravity.example.com/ws/gravity/`

Initial client may send viewport/subscription message.

For hackathon simplicity, backend may broadcast relevant global changes.

Event envelope:

```json
{
  "type": "participant.joined",
  "timestamp": "...",
  "payload": {
    "session_id": "uuid",
    "activity_slug": "basketball",
    "participant_count": 8
  }
}
```

Other event types:

```text
session.created
session.updated
session.ended
participant.joined
participant.left
participant.metrics_updated
event.published
challenge.updated
```

---

# 22. Idempotency

Important reward/leave operations should be idempotent where practical.

Examples:

- finishing Participation twice must not grant XP twice,
- accepting an already accepted challenge should not duplicate participant rows,
- event reward should only be granted once.

Use DB constraints/transactions, not client assumptions.

---

# 23. Permissions

Rules:

- users edit only own participation/metrics,
- staff config via Admin,
- event rewards server-calculated,
- exact friend-only location returned only to authorized friends,
- hidden users never become identifiable through map API.

---

# 24. API Versioning

Not necessary for hackathon.

If added later:

`/api/v1/...`

Do not spend V1 time on versioning infrastructure.
