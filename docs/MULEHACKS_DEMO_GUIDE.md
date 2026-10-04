# Gravity — MuleHacks 2026 Live Demo Guide & Pitch Playbook

**Production URL**: [https://gravity.college](https://gravity.college)  
**Campus Center**: Muhlenberg College (`40.5985`, `-75.5085`)  
**Hackathon Event**: MuleHacks 2026 Activity Boost (2x XP Multiplier)  

---

## 1. The 2-Minute Pitch

> *"Every day on campus, students want to find a pickup basketball game, gym partner, or study group, but coordination across group chats is noisy and fractured. Gravity is the real-time social athletic and campus pulse platform that shows where campus energy is gathering right now—and where it will be next.*
>
> *Powered by PostGIS spatial clustering, privacy-preserving coarse grids, and diurnal recurrence forecasting, Gravity turns spontaneous activity into community without ever tracking private home locations or compromising student safety."*

---

## 2. Seeded Demo Personas

All accounts use the common demo password: **`MuleHacks2026!`**

| Username | Name | Level / XP | Privacy Mode | Role / Demo Purpose |
|---|---|---|---|---|
| `demo_alex` | Alex Rivera | Level 5 (2150 XP) | Friends | Primary demo driver, connected with Jordan and Sam, leading season standings. |
| `demo_jordan` | Jordan Hayes | Level 4 (1420 XP) | Blurred | Host of the live East Court Pickup Game, challenged by Alex in Pickleball. |
| `demo_sam` | Sam Patel | Level 3 (850 XP) | Exact | East Court participant and gym enthusiast. |
| `demo_taylor` | Taylor Brooks | Level 2 (320 XP) | Blurred | Non-friend student hosting Library Study; demonstrates stranger privacy blurring. |

---

## 3. Step-by-Step 2-Minute Demo Route

### Step 1: Live Campus Map & Pulse Now (30 seconds)
1. Navigate to [https://gravity.college](https://gravity.college) and sign in as `demo_alex`.
2. Inspect the **Live Campus Map**:
   - Three active sessions pinned on the Muhlenberg campus map.
   - Notice the **MuleHacks 2026 Activity Boost** 2x XP banner and pulsing activity markers.
3. Open the **Pulse Now** tab:
   - Observe live cards sorted by proximity:
     - **East Court Pickup Game** (Basketball • 2 active participants • "Nearby").
     - **Library Group Study** (Studying • 1 active participant • "Nearby").
     - **Campus Perimeter Jog** (Running • 1 active participant • "~0.2 mi").
   - Highlight: Distance display is privacy-generalized ("Nearby", "<0.5 mi") rather than exposing raw student coordinates.

### Step 2: Pulse Soon & Predictive Forecasting (30 seconds)
1. Switch to the **Pulse Soon** tab or view the hatched overlay on the map.
2. Observe the predicted session:
   - **Basketball Recurrence Forecast**: Sunday 2:00 PM – 4:00 PM (`85% confidence score`, `Very strong pattern`).
   - Click the forecast card to reveal the evidence drawer:
     - 4 occurrences across the last 4 matching Sunday diurnal windows.
     - Typical participants: 4 students.
     - Spatial aggregation: 300m generalized cell polygon.
3. Highlight to judges: *"Gravity doesn't just show current activity—it anticipates campus routines through privacy-safe historical diurnal clustering."*

### Step 3: Area History & Privacy Safeguards (20 seconds)
1. Click **Area History** for Muhlenberg Center:
   - Dominant activity: **Basketball** (42.9% share, 9 participations).
   - Diurnal distribution chart: Peak activity between 12:00 – 15:00.
   - Busiest day: Monday / weekend athletic peaks.
2. Note the strict privacy safeguard: If fewer than 3 unique users have participated, the area history is automatically suppressed with a privacy notice.

### Step 4: Gamification, Events & Challenges (25 seconds)
1. Navigate to **Challenges & Leaderboard**:
   - Active Friend Challenge: *"[Demo] First to 5 Pickleball Wins"* between Alex (3/5) and Jordan (2/5).
   - Season Standings: *MuleHacks Season 1* basketball leaderboard showing Alex at #1 (1250 XP).
   - User profile: Alex has 4 badges (*Early Adopter*, *Century Club*, *Century Club Elite*, *Night Owl*) and a 14-day streak.

### Step 5: Quick-Join & Auto-Stop (15 seconds)
1. Show the **QR Code Quick Join** modal for active sessions.
2. Mention the **Auto-Stop engine**: Sessions geofence participants with an anchor radius (default 100m) and grace period, automatically stopping inactive or departed sessions to prevent ghost sessions on campus.

---

## 4. Emergency Demo Reset

If data is altered during live testing or judging, run the one-command idempotent reset on the server:

```bash
cd /home/mule/gravity
backend/venv/bin/python backend/manage.py seed_demo --reset
```

Optional custom campus center coordinates:
```bash
backend/venv/bin/python backend/manage.py seed_demo --reset --lat 40.5985 --lng -75.5085
```
