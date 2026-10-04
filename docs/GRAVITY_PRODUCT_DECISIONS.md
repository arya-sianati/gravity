# Gravity — Locked Product Decisions

This file records explicit product decisions so earlier brainstorm ideas do not creep back into the implementation.

## Core identity

**Name:** Gravity

**Concept:** A live map of human activity. Activities generate visible geographic "gravity" based on how many people are participating and how intense/current the activity is.

## Activities

V1 has platform-defined activity categories.

Initial categories:

- Basketball
- Running
- Gaming
- Studying
- Workout
- Soccer
- Other

Users do **not** create new official activity categories in V1.

`Other` acts as a discovery funnel. Admins can later promote repeatedly trending "Other" activities into official categories.

## Communities

V1 does **not** include user-created communities.

"Basketball community" means the overall population participating in Basketball on Gravity, not a user-created group such as "UCM Basketball Club."

Community creation can be a future feature.

## Map geography

V1 does not require manually defined areas such as:

- campus,
- recreation center,
- neighborhood,
- building,
- court,
- city zone.

The map is geographic and activity is clustered by proximity.

Two basketball games on neighboring courts can visually contribute to one Basketball hotspot if close enough.

Two basketball games far apart, such as one at a recreation center and one at a distant park, should appear as separate Basketball hotspots.

## Competition between activities

Activities do not conquer territory.

Multiple activities can exist in the same location at the same time.

The map visually shows relative crowd/activity intensity through heatmap intensity, saturation, opacity, and overlapping colors.

Example:

- Basketball may be the strongest/darkest layer.
- Running may be visible underneath or beside it as a lighter heat layer.
- Gaming may also overlap.

Historical results can rank activities at a location/time period after live activity fades.

## Live-first design

Gravity primarily represents activity happening **now**.

Starting an activity creates a live Gravity Drop.

Users may:

- start their own participation,
- join an existing nearby session,
- scan a QR code to join quickly.

The system may suggest joining an existing nearby session, but database sessions can remain separate even when their map heat is aggregated geographically.

## QR behavior

A session starter can display a join QR code.

Scanning it should open a join page and allow fast participation.

QR is convenience, not a mandatory verification system.

## Self-reporting and verification

Self-reporting is allowed.

Gravity should not communicate distrust toward users.

Internally, participation may record verification/context such as:

- self-reported,
- QR joined,
- location-confirmed,
- GPS tracked.

Verification can influence future scoring or integrity systems, but V1 should be permissive.

## Activity-specific metrics

Each activity can use different meaningful metrics.

Examples:

- Running: miles/distance
- Basketball: points
- Gaming: wins and/or time
- Studying: time
- Workout: duration or configurable metric
- Soccer: goals or time

Activity-specific leaderboards use the activity's own configured metric.

Personal Gravity XP is separate from activity leaderboard metrics.

## Personal progression

Users have a combined personal progression system:

- Gravity XP
- Level
- badges
- streaks/consistency
- event rewards
- season progress

The initial XP formula can be simple.

Additional XP variables can be added later.

## Seniority

Joining an activity/category earlier does not provide an XP multiplier.

The system may show:

- how long the user has participated in the activity,
- badges,
- historical status/tenure.

No permanent score advantage should come from early membership in V1.

## Seasons

Seasons are included.

Seasons provide:

- season XP/progression,
- seasonal rankings,
- seasonal badges/rewards,
- a historical season record on user profiles.

Historical achievements persist after a season ends.

## Gravity Events

Platform admins can create official Gravity Events.

Example:

**Basketball Week**

Possible event configuration:

- start/end dates,
- bonus XP,
- badge reward,
- featured activity,
- participation requirement.

Official events should encourage people to try or revisit activities.

## Recurring activity recognition

Gravity can learn recurring activity patterns from live session history.

Example:

If Basketball repeatedly occurs in roughly the same geographic area on weekdays around 6–8 PM, Gravity can suggest:

> Basketball is likely to happen here soon.

No community-owned scheduled event is required.

## Pulse

Gravity includes a discovery action called **Pulse**.

Pulse should surface the most relevant nearby live activity.

Two conceptual modes:

- **Pulse Now** — activity happening now
- **Pulse Soon** — likely recurring activity expected soon

Pulse Soon should use a distinct visual style such as a hatched/patterned heat region rather than the solid live heatmap.

## Friends

Gravity can have friends similar to Duolingo.

Friends can see permitted activity/progression information such as:

- activity started,
- levels,
- badges,
- streaks,
- challenge progress.

Exact location depends on privacy settings.

## Friend challenges

Friends can challenge each other.

Possible challenge types:

- first to a target,
- highest activity metric in a time window,
- cooperative combined target.

Examples:

- run 10 miles this week,
- most Basketball points by Sunday,
- study 10 combined hours.

## Feed

A richer Instagram-like social feed with activity photos is a future feature.

It is not required for V1.

## Privacy

Location privacy is user-controlled.

V1 modes:

- Hidden
- Blurred/Approximate
- Friends-only
- Exact

Home/private-location activity should default to blurred/approximate.

Approximate location should be represented as an area that contains the true location rather than a marker centered exactly on the residence.

Users may explicitly opt into precise location sharing.

## Auto-stop

Activity types may define location-based auto-stop rules.

Example:

Basketball may auto-stop after the user leaves the session area and remains away beyond a grace period.

Running should not use this same rule because movement is the activity.

Auto-stop behavior must be configurable per activity type.

## Heatmap design

The map should use heatmap-like geographic color fields, not fixed circles.

Each activity has its own admin-defined base color.

Activity strength is expressed through combinations of:

- opacity,
- saturation,
- heat intensity,
- density.

Multiple activity colors may overlap.

The dominant activity can appear more saturated while lower-intensity activities remain visible as lighter shades.

## History and reputation

Gravity may preserve historical information for an area based on geographic proximity, even without named venues.

Examples:

- today's peak activity,
- week's most active category,
- previous season's strongest category,
- recurring time patterns.

This creates geographic "reputation" without manually defining territories.
