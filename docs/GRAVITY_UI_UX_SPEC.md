# Gravity — UI/UX Specification

# 1. Visual Direction

Gravity should feel like a live map/game/social product, not an enterprise dashboard.

Primary characteristics:

- dark or map-forward visual treatment is acceptable,
- activity colors are vivid,
- live heat is the main visual identity,
- controls are thumb-friendly,
- mobile-first,
- concise text,
- cards/sheets overlay the map rather than replacing it unnecessarily.

Do not overdesign before the live map works.

---

# 2. App Shell

Suggested bottom navigation:

- Map
- Pulse
- Start
- Friends
- Profile

`Start` may be a larger central action.

Alternative:
Keep only Map/Friends/Profile in nav and place Pulse + Start as floating map controls.

Prefer whichever gives the map more space.

---

# 3. Map Screen

Must include:

- full-screen map,
- live heat layers,
- current-location/recenter button,
- Pulse button,
- Start Activity button,
- filter control,
- optional small event banner.

Interaction:

- tap live heat/hotspot → bottom sheet,
- pan/zoom updates map query after debounce,
- changing filters hides/shows activity layers.

### Hotspot bottom sheet

Show:

- activity icon/name,
- approximate strength,
- active participant count,
- distance,
- Join button where appropriate,
- activity leaderboard shortcut,
- official event indicator if active.

If multiple activities overlap:

```text
What's happening here

🏀 Basketball   24 active
🏃 Running       9 active
🎮 Gaming        4 active
```

Order by current strength.

---

# 4. Heatmap

Live heat:

- smooth,
- colored,
- opacity proportional to strength,
- darker/more saturated as intensity grows.

Forecast heat:

- lighter,
- hatched/patterned,
- clearly labeled "Expected" or "Soon."

Do not use fixed hard circles as the main visualization.

Approximate privacy areas can use soft/blurred fields.

---

# 5. Start Activity Flow

Step 1:
Activity grid/list.

```text
What are you doing?

🏀 Basketball
🏃 Running
🎮 Gaming
📚 Studying
🏋️ Workout
⚽ Soccer
✨ Other
```

Step 2:
If `Other`, optional short label.

Step 3:
If nearby matching live session exists:

```text
Basketball is already happening nearby.

8 active • 300 ft away

[ Join ]
[ Start separately ]
```

Step 4:
Start.

Avoid long forms.

---

# 6. Active Activity Screen

Header:
- icon + activity name
- LIVE indicator

Body:
- elapsed duration
- participant count
- configured metrics
- event bonus if active
- small map/area optional

Actions:
- Show Join QR
- Update Metrics
- Leave / Finish

Example:

```text
🏀 Basketball     LIVE

42:18
8 active

Your points
17

Basketball Week
2× XP

[ Show Join QR ]

[ Finish ]
```

---

# 7. QR Screen

Large QR.

Show:

- Activity Type
- participant count
- short text:
  "Scan to join this Basketball activity"

Optional:
- copy/share join link.

Avoid embedding sensitive info visually.

---

# 8. Join Landing

After QR scan:

```text
🏀 Basketball

8 people active
Started 21 min ago

[ Join Activity ]
```

If not logged in:
- sign in/register,
- then continue original join intent.

---

# 9. Metric Entry

Generate form dynamically from ActivityMetric config.

Basketball:

```text
Points
[ 17 ]

Minutes
[ auto / 42 ]
```

Running:

```text
Distance
[ 3.42 ] miles

Duration
[ 31:08 ]
```

Keep fast.

---

# 10. Pulse

Pulse opens a sheet/page.

Tabs:

- Now
- Soon (when implemented)

## Now card

```text
🔥 Basketball
24 active
0.3 mi
Very active

[ View ]
```

Possible event card:

```text
🏀 Basketball Week
2× XP
Ends Sunday
```

## Soon card

```text
//// 🏀 Basketball
Expected around 6:00 PM
Typical: 12–18 active
0.5 mi
```

---

# 11. Leaderboard

Top:

- activity selector or current Activity Type,
- period tabs:
  - Today
  - Week
  - Season
  - All Time

Rows:

```text
1  Maya     184 pts
2  Alex     171 pts
3  You      163 pts
```

Pin/highlight current user if outside visible top results.

---

# 12. Profile

Header:
- display name
- Gravity Level
- XP progress

Sections:

- current streak,
- badges,
- activity stats,
- season summary,
- friends count,
- activity tenure.

Example:

```text
Level 18
4,820 XP

🔥 12 day streak

Top activities
🏀 Basketball
🏃 Running
🎮 Gaming

Season 1
#14 Basketball
6 badges
```

---

# 13. Friends

Friend list + recent friend activity.

Examples:

```text
Alex
🏃 Running now
Level 14

Sarah
Earned 🔥 7-Day Streak
```

Location shown only according to privacy.

---

# 14. Challenges

Create form:

- friend(s),
- Activity Type,
- metric,
- mode,
- target,
- deadline.

Active challenge:

```text
🏃 Arya vs Alex

Run 10 miles first

Arya   6.2
Alex   7.1
```

---

# 15. Events

Event UI should clearly show:

- activity,
- dates,
- reward,
- progress,
- badge.

Example:

```text
🏀 Basketball Week

Oct 12–18
+250 XP
Limited Badge

Your progress
42 / 60 min
```

---

# 16. Seasons

Profile/season screen:

```text
Season 1

Level / XP
Activity ranks
Badges
Streak
Event completions
```

After season ends:
display historical card rather than deleting.

---

# 17. Privacy Settings

Simple options:

```text
Location visibility

○ Hidden
● Approximate
○ Friends
○ Exact
```

Explain each in one sentence.

Approximate should be recommended/default for home/private activity.

---

# 18. Loading/Error States

Map:
- skeleton/loader while configuration loads,
- retry if map data fails.

Location denied:
- do not block entire app,
- concise explanation,
- allow browsing.

WebSocket disconnected:
- subtle "Reconnecting..." state,
- REST refresh fallback.

---

# 19. Accessibility

- do not communicate activity solely through color,
- always use icons/text in lists/details,
- adequate touch targets,
- readable text over map,
- bottom sheets should be screen-reader navigable where feasible.

---

# 20. Hackathon UI Order

Polish in this order:

1. Map + heat
2. Start Activity
3. Active Activity
4. QR Join
5. Pulse
6. Leaderboard
7. Profile
8. Event
9. Friends
10. Challenge

Do not spend time polishing Profile while map heat is unstable.
