import math
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance

from activities.models import ActivitySession, Participation, ActivityType, GravityEvent
from activities.logic.pulse_service import format_privacy_safe_distance

# Grid step approximation for coarse spatial clustering (~350m cells)
GRID_STEP_LAT = 0.0035
GRID_STEP_LNG = 0.0035
DEFAULT_CELL_RADIUS_M = 300.0

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def snap_to_grid(lat: float, lng: float) -> tuple[float, float]:
    """
    Snaps raw coordinates to a deterministic, coarse geographic grid cell (~350m wide).
    Protects user privacy by generalizing exact historical coordinates.
    """
    snapped_lat = round(round(lat / GRID_STEP_LAT) * GRID_STEP_LAT, 5)
    snapped_lng = round(round(lng / GRID_STEP_LNG) * GRID_STEP_LNG, 5)
    return snapped_lat, snapped_lng


def generate_cell_polygon(center_lat: float, center_lng: float, radius_m: float = DEFAULT_CELL_RADIUS_M, num_points: int = 16) -> list:
    """
    Generates a 16-point circular polygon in GeoJSON format [[[lng, lat], ...]].
    Used by frontend MapLibre layers for patterned/hatched forecast region overlays.
    """
    ring = []
    for i in range(num_points + 1):
        angle = (2.0 * math.pi * i) / num_points
        d_lat = (radius_m * math.cos(angle)) / 111320.0
        d_lng = (radius_m * math.sin(angle)) / (111320.0 * math.cos(math.radians(center_lat)))
        ring.append([round(center_lng + d_lng, 6), round(center_lat + d_lat, 6)])
    return [ring]


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Computes approximate distance in meters between two coordinates."""
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_forecast_confidence(
    distinct_weeks: int,
    eligible_weeks: int,
    avg_participants: float,
    days_since_latest: float,
) -> float:
    """
    Computes an explainable, bounded [0.0, 1.0] confidence score for a candidate recurring pattern.
    confidence = (0.55 * recurrence_score) + (0.30 * volume_score) + (0.15 * recency_score)
    """
    # 1. Recurrence across weeks (target: 4+ distinct weeks gives 1.0)
    recurrence_score = min(1.0, float(distinct_weeks) / 4.0)

    # 2. Historical volume strength (target: 8+ average participants gives 1.0)
    volume_score = min(1.0, float(avg_participants) / 8.0)

    # 3. Recency decay (observations in last 2 weeks are strongest)
    if days_since_latest <= 14.0:
        recency_score = 1.0
    elif days_since_latest <= 28.0:
        recency_score = 0.75
    elif days_since_latest <= 42.0:
        recency_score = 0.50
    else:
        recency_score = 0.25

    confidence = (0.55 * recurrence_score) + (0.30 * volume_score) + (0.15 * recency_score)
    return round(max(0.0, min(1.0, confidence)), 2)


def get_pulse_soon(
    lat: float,
    lng: float,
    radius_m: float = None,
    horizon_minutes: int = None,
    activity_slug: str = None,
    limit: int = 20,
    now: datetime = None,
) -> dict:
    """
    Generates historical recurring activity forecasts for the near-future horizon (default 2 hours)
    around (lat, lng) within radius_m.

    Adheres strictly to privacy safeguards:
    - Minimum unique users threshold (GRAVITY_HISTORY_MIN_PARTICIPANTS)
    - Minimum recurrence across distinct weeks (GRAVITY_FORECAST_MIN_OCCURRENCES)
    - Coarse geographic grid cells (never raw historical coordinates)
    - Suppresses predictions where matching live activity is already running
    """
    if now is None:
        now = timezone.now()

    # 1. Validate inputs
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        raise ValueError("Latitude and Longitude must be valid numbers.")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not (-180.0 <= lng <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    default_radius = getattr(settings, 'GRAVITY_PULSE_DEFAULT_RADIUS_M', 5000)
    max_radius = getattr(settings, 'GRAVITY_PULSE_MAX_RADIUS_M', 50000)

    if radius_m is None:
        radius_m = float(default_radius)
    else:
        try:
            radius_m = float(radius_m)
            if radius_m <= 0:
                raise ValueError("Radius must be greater than 0.")
            radius_m = min(radius_m, float(max_radius))
        except (ValueError, TypeError):
            raise ValueError("Radius must be a valid number.")

    default_horizon = getattr(settings, 'GRAVITY_FORECAST_HORIZON_MINUTES', 120)
    if horizon_minutes is None:
        horizon_minutes = int(default_horizon)
    else:
        try:
            horizon_minutes = int(horizon_minutes)
            if horizon_minutes <= 0:
                raise ValueError("horizon_minutes must be greater than 0.")
        except (ValueError, TypeError):
            raise ValueError("horizon_minutes must be a valid number.")

    lookback_days = getattr(settings, 'GRAVITY_FORECAST_LOOKBACK_DAYS', 56)
    min_occurrences = getattr(settings, 'GRAVITY_FORECAST_MIN_OCCURRENCES', 3)
    min_participants = getattr(settings, 'GRAVITY_HISTORY_MIN_PARTICIPANTS', 3)
    min_confidence = getattr(settings, 'GRAVITY_FORECAST_MIN_CONFIDENCE', 0.55)
    min_duration = getattr(settings, 'GRAVITY_MIN_XP_DURATION_SECONDS', 60)

    lookback_cutoff = now - timedelta(days=lookback_days)
    user_point = Point(lng, lat, srid=4326)

    # 2. Live Duplicate Suppression Set
    # Find active sessions within query radius to prevent duplicate "Soon" predictions
    active_sessions = ActivitySession.objects.filter(
        status=ActivitySession.Status.ACTIVE,
        location__distance_lte=(user_point, D(m=radius_m + DEFAULT_CELL_RADIUS_M)),
    ).select_related('activity_type')

    live_cell_activities = set()
    for live_sess in active_sessions:
        s_lat, s_lng = snap_to_grid(live_sess.location.y, live_sess.location.x)
        live_cell_activities.add((live_sess.activity_type_id, s_lat, s_lng))

    # 3. Query historical sessions in spatial & lookback window
    session_qs = ActivitySession.objects.filter(
        location__distance_lte=(user_point, D(m=radius_m + DEFAULT_CELL_RADIUS_M)),
        started_at__gte=lookback_cutoff,
        started_at__lte=now,
    ).exclude(status=ActivitySession.Status.CANCELLED).select_related('activity_type')

    if activity_slug:
        session_qs = session_qs.filter(activity_type__slug=activity_slug)

    # Filter qualifying concluded participations
    participations_qs = Participation.objects.filter(
        session__in=session_qs,
        status__in=[
            Participation.Status.COMPLETED,
            Participation.Status.LEFT,
            Participation.Status.AUTO_STOPPED,
        ],
    ).select_related('session', 'session__activity_type')

    # Collect valid sessions and participations
    valid_sessions = {}
    valid_participations = []

    for p in participations_qs:
        dur = 0.0
        if p.left_at is not None:
            dur = (p.left_at - p.joined_at).total_seconds()
        elif p.session.ended_at is not None:
            dur = (p.session.ended_at - p.joined_at).total_seconds()
        else:
            dur = (p.updated_at - p.joined_at).total_seconds()
            if dur <= 0:
                dur = float(min_duration)

        if dur >= min_duration:
            valid_participations.append(p)
            valid_sessions[p.session_id] = p.session

    if not valid_participations:
        return {"items": []}

    # 4. Spatially snap sessions and cluster into (activity_type, cell, weekday, 2-hour window)
    clusters = {}
    for p in valid_participations:
        sess = p.session
        act = sess.activity_type

        # Grid snapping for coarse cell
        cell_lat, cell_lng = snap_to_grid(sess.location.y, sess.location.x)

        # Convert timestamp to local application timezone
        ref_dt = sess.started_at
        local_dt = timezone.localtime(ref_dt)
        weekday = local_dt.weekday() # 0 = Monday, 6 = Sunday

        # 2-Hour window (0-2, 2-4, ..., 18-20, 20-22, 22-24)
        start_hour = (local_dt.hour // 2) * 2
        end_hour = start_hour + 2

        cluster_key = (act.id, cell_lat, cell_lng, weekday, start_hour)
        if cluster_key not in clusters:
            clusters[cluster_key] = {
                "activity_type": act,
                "cell_lat": cell_lat,
                "cell_lng": cell_lng,
                "weekday": weekday,
                "start_hour": start_hour,
                "end_hour": end_hour,
                "sessions": set(),
                "participations": [],
                "user_ids": set(),
                "distinct_weeks": set(),
                "latest_occurrence_dt": ref_dt,
            }

        clusters[cluster_key]["sessions"].add(sess.id)
        clusters[cluster_key]["participations"].append(p)
        clusters[cluster_key]["user_ids"].add(p.user_id)

        # Track distinct calendar weeks (year, week)
        iso_year, iso_week, _ = local_dt.isocalendar()
        clusters[cluster_key]["distinct_weeks"].add((iso_year, iso_week))

        if ref_dt > clusters[cluster_key]["latest_occurrence_dt"]:
            clusters[cluster_key]["latest_occurrence_dt"] = ref_dt

    # 5. Evaluate Candidate Forecasts against near-future horizon
    local_now = timezone.localtime(now)
    horizon_end = local_now + timedelta(minutes=horizon_minutes)
    eligible_weeks = max(1, lookback_days // 7)

    # Fetch live/upcoming Gravity Events for bonus decoration
    live_events = list(GravityEvent.objects.filter(
        is_active=True,
        starts_at__lte=horizon_end,
        ends_at__gte=now,
    ).select_related('activity_type'))

    forecast_items = []

    for cluster in clusters.values():
        act = cluster["activity_type"]
        cell_lat = cluster["cell_lat"]
        cell_lng = cluster["cell_lng"]
        weekday = cluster["weekday"]
        start_hour = cluster["start_hour"]
        end_hour = cluster["end_hour"]

        sess_count = len(cluster["sessions"])
        part_count = len(cluster["participations"])
        unique_users_count = len(cluster["user_ids"])
        distinct_weeks_count = len(cluster["distinct_weeks"])
        latest_dt = cluster["latest_occurrence_dt"]

        # Check Privacy & Recurrence Thresholds
        # Both min unique users AND min recurring weeks MUST be satisfied!
        if unique_users_count < min_participants:
            continue
        if distinct_weeks_count < min_occurrences:
            continue
        if sess_count < min_occurrences:
            continue

        # Check Live Duplicate Suppression
        # If this activity is ALREADY active in this coarse cell right now, suppress Soon prediction
        if (act.id, cell_lat, cell_lng) in live_cell_activities:
            continue

        # Calculate Expected Window on today's/tomorrow's calendar
        # Determine candidate target date:
        # If weekday matches local_now.weekday(): candidate is today
        # If weekday matches (local_now.weekday() + 1) % 7 and local_now.hour >= 20: candidate is tomorrow
        window_dt_start = None
        window_dt_end = None

        if weekday == local_now.weekday():
            w_start = local_now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            w_end = w_start + timedelta(hours=2)
            # Check horizon match:
            # Starts in the future within horizon, OR window is currently in progress
            if (local_now <= w_start <= horizon_end) or (w_start <= local_now < w_end):
                window_dt_start = w_start
                window_dt_end = w_end

        elif weekday == (local_now.weekday() + 1) % 7:
            # Tomorrow
            tomorrow = local_now + timedelta(days=1)
            w_start = tomorrow.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            w_end = w_start + timedelta(hours=2)
            if local_now <= w_start <= horizon_end:
                window_dt_start = w_start
                window_dt_end = w_end

        if not window_dt_start:
            # Not within upcoming near-term horizon
            continue

        # Check Distance from user center
        dist_m = haversine_distance_m(lat, lng, cell_lat, cell_lng)
        if dist_m > (radius_m + DEFAULT_CELL_RADIUS_M):
            continue

        # Compute Confidence Score
        avg_participants = float(part_count) / float(sess_count)
        days_since_latest = max(0.0, (now - latest_dt).total_seconds() / 86400.0)

        confidence = compute_forecast_confidence(
            distinct_weeks=distinct_weeks_count,
            eligible_weeks=eligible_weeks,
            avg_participants=avg_participants,
            days_since_latest=days_since_latest,
        )

        if confidence < min_confidence:
            continue

        # Determine Confidence Level & Human-Readable Labels
        if confidence >= 0.85:
            conf_level = "very_strong"
            conf_display = "Very strong pattern"
        elif confidence >= 0.70:
            conf_level = "strong"
            conf_display = "Strong pattern"
        else:
            conf_level = "moderate"
            conf_display = "Moderate pattern"

        # Format Expected Window display
        start_fmt = window_dt_start.strftime("%-I:%M %p")
        end_fmt = window_dt_end.strftime("%-I:%M %p")
        window_display = f"{start_fmt} – {end_fmt}"

        weekday_name = WEEKDAYS[weekday]
        reason = f"Active here on {distinct_weeks_count} of the last {eligible_weeks} {weekday_name}s • Usually active {window_display}"

        # Match active or upcoming Gravity Event
        matching_event = None
        for ev in live_events:
            if ev.activity_type_id is None or ev.activity_type_id == act.id:
                matching_event = {
                    "name": ev.name,
                    "slug": ev.slug,
                    "xp_multiplier": ev.xp_multiplier,
                    "flat_xp_bonus": ev.flat_xp_bonus,
                    "badge_icon": ev.badge.icon if ev.badge else None,
                }
                break

        # Generate coarse circular polygon geometry for map rendering
        cell_geom = generate_cell_polygon(cell_lat, cell_lng, radius_m=DEFAULT_CELL_RADIUS_M)

        forecast_items.append({
            "activity": {
                "id": act.id,
                "slug": act.slug,
                "name": act.name,
                "icon": act.icon,
                "color": act.color,
            },
            "area": {
                "lat": cell_lat,
                "lng": cell_lng,
                "radius_m": int(DEFAULT_CELL_RADIUS_M),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": cell_geom,
            },
            "distance": {
                "raw_m": round(dist_m, 1),
                "display": format_privacy_safe_distance(dist_m),
            },
            "expected_window": {
                "starts_at": window_dt_start.isoformat(),
                "ends_at": window_dt_end.isoformat(),
                "display": window_display,
            },
            "confidence_score": confidence,
            "confidence_level": conf_level,
            "confidence_display": conf_display,
            "historical_evidence": {
                "matching_weeks": distinct_weeks_count,
                "total_lookback_weeks": eligible_weeks,
                "observations": sess_count,
                "typical_participants": int(round(avg_participants)),
                "unique_users": unique_users_count,
            },
            "reason": reason,
            "event": matching_event,
        })

    # 6. Forecast Ordering:
    # 1. confidence_score desc
    # 2. window starts_at asc (sooner first)
    # 3. typical_participants desc
    # 4. distance_m asc
    # 5. activity slug asc
    forecast_items.sort(
        key=lambda x: (
            -x["confidence_score"],
            x["expected_window"]["starts_at"],
            -x["historical_evidence"]["typical_participants"],
            x["distance"]["raw_m"],
            x["activity"]["slug"],
        )
    )

    if limit and limit > 0:
        forecast_items = forecast_items[:limit]

    return {"items": forecast_items}
