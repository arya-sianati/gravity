# Gravity — Proposed Data Model

This is a detailed proposed model, not a prohibition against small implementation adjustments.

---

# 1. User

Use a custom Django user model.

Core fields:

```text
id
username/email
display_name
password hash
total_xp
current_level
location_privacy_mode
created_at
updated_at
```

Potential later:

```text
avatar
bio
home_region generalized
```

---

# 2. Friendship

```text
id
requester
addressee
status
created_at
accepted_at
```

Status:

- pending
- accepted
- rejected
- blocked

Unique pair constraint should prevent duplicate active friendships.

---

# 3. ActivityType

```text
id
name
slug
icon
color
description
is_active
sort_order

cluster_radius_m
join_suggestion_radius_m

self_start_enabled
qr_join_enabled
gps_tracking_enabled

auto_stop_enabled
auto_stop_radius_m
auto_stop_grace_seconds

default_xp
heat_weight_multiplier

created_at
updated_at
```

Possible later:

```text
privacy_default
minimum_duration
forecast_enabled
```

---

# 4. ActivityMetric

```text
id
activity_type
name
slug
unit
data_type

aggregation
is_primary
leaderboard_enabled
required

min_value
max_value
xp_weight
sort_order

created_at
updated_at
```

Data types:

- integer
- decimal
- duration
- boolean

Aggregation:

- sum
- max
- average
- latest

V1 will mostly use `sum`.

Constraint:
- at most one primary metric per Activity Type unless explicitly designed otherwise.

---

# 5. ActivitySession

```text
id / UUID
activity_type
created_by
label optional

location PointField
status

started_at
ended_at

join_token
join_token_expires_at optional

created_at
updated_at
```

Status:

- active
- ended
- cancelled

Possible later:

```text
title
notes
event
source
```

---

# 6. Participation

```text
id
session
user

status
joined_at
left_at

join_method
verification_context

outside_since optional
last_location_heartbeat_at optional

created_at
updated_at
```

Status:

- active
- completed
- left
- auto_stopped

Join method:

- self
- qr
- map
- suggestion
- invite

Verification context may be JSON for non-sensitive flags, for example:

```json
{
  "qr_joined": true,
  "location_confirmed": true,
  "gps_tracked": false
}
```

Do not use JSON as a dumping ground for core relational data.

Unique constraint:
- one active participation per user per session.

Business rule:
- decide whether user may be active in multiple Activity Types simultaneously. V1 recommendation: one active participation at a time unless a strong use case requires otherwise.

---

# 7. MetricValue

Recommended model supporting updates and final values.

```text
id
participation
metric
value_decimal
recorded_at
is_final
```

Alternative typed fields can be used if desired.

For simple V1, normalize numeric/duration values to decimal seconds/units where sensible.

Examples:

- Basketball points = 17
- Running miles = 3.42
- Study duration seconds = 5400

Unique final value per participation+metric if using snapshot model.

If metrics need time series later, create separate samples.

---

# 8. XPTransaction

```text
id
user
amount
reason
description

season optional
activity_type optional
participation optional
gravity_event optional
challenge optional

created_at
```

Reasons:

- participation
- event
- streak
- badge
- challenge
- admin
- adjustment

`total_xp` can be cached on User but ledger is source of audit truth.

---

# 9. Badge

```text
id
name
slug
description
icon
is_active
rarity optional
created_at
```

---

# 10. UserBadge

```text
id
user
badge
earned_at

gravity_event optional
season optional
activity_type optional
metadata optional
```

Unique constraints depend on repeatability.

V1 recommendation:
- most badges unique once per user,
- event badges can be unique per event.

---

# 11. GravityEvent

```text
id
title
slug
description

activity_type
starts_at
ends_at

is_published
is_active_override optional

xp_multiplier
flat_completion_xp
minimum_duration_seconds optional
minimum_metric optional
minimum_metric_value optional

badge optional

created_at
updated_at
```

Do not require both flat reward and multiplier.

---

# 12. EventParticipation / EventProgress

If event completion cannot be calculated cheaply from normal participation data, use:

```text
id
event
user
progress_value
completed_at
reward_granted_at
```

For V1, this can be derived unless convenient to store.

---

# 13. Season

```text
id
name
slug
number optional
starts_at
ends_at
is_active
created_at
```

Constraint:
- avoid overlapping active seasons unless explicitly supported.

---

# 14. Streak

Optional dedicated model.

```text
id
user
streak_type
activity_type optional
current_count
longest_count
last_qualified_date
updated_at
```

For V1, personal daily activity streak is enough.

---

# 15. FriendChallenge

```text
id
created_by
activity_type
metric
mode

target_value optional
starts_at
ends_at
status

created_at
updated_at
```

Modes:

- first_to_target
- highest_by_deadline
- cooperative_target

---

# 16. ChallengeParticipant

```text
id
challenge
user
status
joined_at
final_value
rank optional
```

---

# 17. ForecastCluster

P2 optional cache model.

```text
id
activity_type
center PointField
radius_m

weekday
start_time_bucket

observation_count
typical_start_time
typical_end_time
typical_participants
confidence

valid_from
valid_until
updated_at
```

Can instead compute dynamically for hackathon demo.

---

# 18. ActivityTrend

Future optional model for `Other` discovery.

```text
id
normalized_label
count
period_start
period_end
promoted_activity_type optional
```

---

# 19. Privacy

Recommended enum on User:

```text
hidden
blurred
friends
exact
```

Potential per-session override later.

For V1, user-level default plus optional active-session override is sufficient.

---

# 20. Indexes

Important database indexes:

### ActivitySession
- spatial GiST index on location
- status
- started_at
- activity_type + status

### Participation
- session + status
- user + status
- joined_at

### MetricValue
- metric
- participation
- recorded_at

### XPTransaction
- user + created_at
- season

### Friendship
- requester/status
- addressee/status

---

# 21. Constraints / Integrity

Recommended:

- ActivityType slug unique
- ActivityMetric unique `(activity_type, slug)`
- ActivitySession join_token unique
- Friendship duplicate-pair prevention
- Challenge participant unique `(challenge, user)`
- UserBadge uniqueness according to badge repeatability
- only valid metric values for metrics belonging to participation session Activity Type
- event metric, if configured, must belong to event Activity Type

---

# 22. Deletion Strategy

Prefer soft or protected deletion for data that affects history.

Examples:

- ActivityType should generally be disabled rather than deleted after use.
- Sessions should remain historical.
- Metrics used historically should not be casually removed.

User deletion/privacy handling can be enhanced later.

---

# 23. Admin Usability

Django Admin should use:

- ActivityMetric inline under ActivityType
- filters for active sessions
- search by user/activity
- date hierarchy where useful
- readonly timestamps
- clear fieldsets

The admin should be usable by a hackathon operator without touching SQL.
