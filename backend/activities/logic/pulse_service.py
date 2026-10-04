import math
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Count, Q

from activities.models import ActivitySession, Participation, GravityEvent

# Pulse scoring weights and tuning constants
WEIGHT_DISTANCE = 0.40
WEIGHT_PARTICIPATION = 0.35
WEIGHT_RECENCY = 0.25

MAX_RECENCY_MINUTES = 180.0 # Activity recency decays over 3 hours
SATURATION_PARTICIPANTS = 15.0 # Max participant score achieved at 15+ active people

METERS_TO_MILES = 0.000621371

def compute_pulse_score(distance_m: float, participant_count: int, started_at: datetime, now: datetime = None, radius_m: float = 5000.0) -> float:
    """
    Computes a deterministic, bounded [0.0, 1.0] Pulse score.
    Higher score means: closer distance, more active participants, and more recent start.
    """
    if now is None:
        now = timezone.now()

    # 1. Distance Decay (closer is higher)
    ref_radius = max(float(radius_m), 1000.0)
    distance_score = max(0.0, 1.0 - (float(distance_m) / ref_radius))

    # 2. Participant Strength (more active people is higher, bounded)
    participant_score = min(1.0, max(0.0, float(participant_count) / SATURATION_PARTICIPANTS))

    # 3. Recency Decay (newer is higher)
    age_seconds = max(0.0, (now - started_at).total_seconds())
    age_minutes = age_seconds / 60.0
    recency_score = max(0.0, 1.0 - (age_minutes / MAX_RECENCY_MINUTES))

    # Weighted composite score
    composite = (
        (WEIGHT_DISTANCE * distance_score) +
        (WEIGHT_PARTICIPATION * participant_score) +
        (WEIGHT_RECENCY * recency_score)
    )

    return round(max(0.0, min(1.0, composite)), 4)


def format_privacy_safe_distance(distance_m: float, privacy_mode: str, is_owner: bool = False) -> str:
    """
    Formats distance for public serialization without leaking exact coordinates.
    For Blurred and Friends modes (for non-owners), uses coarse bucketed representations.
    """
    dist_mi = distance_m * METERS_TO_MILES

    if (privacy_mode in ['blurred', 'friends']) and not is_owner:
        if distance_m < 400:
            return "Nearby"
        elif distance_m < 800:
            return "<0.5 mi"
        elif distance_m < 1600:
            return "~1 mi"
        else:
            # Round to nearest 0.5 mile
            rounded = round(dist_mi * 2.0) / 2.0
            return f"~{rounded:.1f} mi"
    else:
        # Exact mode or owner viewing their own session
        if dist_mi < 0.1:
            return "<0.1 mi"
        else:
            return f"~{dist_mi:.1f} mi"


def get_pulse_now(user, lat: float, lng: float, radius_m: float = None, activity_slug: str = None, limit: int = 20) -> dict:
    """
    Fetches active nearby sessions scored and formatted for the Pulse Now discovery feed.
    """
    default_radius = getattr(settings, 'GRAVITY_PULSE_DEFAULT_RADIUS_M', 5000)
    max_radius = getattr(settings, 'GRAVITY_PULSE_MAX_RADIUS_M', 50000)

    if radius_m is None:
        radius_m = float(default_radius)
    else:
        radius_m = float(radius_m)
        if radius_m <= 0:
            raise ValueError("Radius must be greater than 0.")
        # Clamp to max radius
        radius_m = min(radius_m, float(max_radius))

    if not (-90.0 <= lat <= 90.0):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180.0 <= lng <= 180.0):
        raise ValueError("Longitude must be between -180 and 180.")

    limit = max(1, min(int(limit), 100))

    user_point = Point(lng, lat, srid=4326)
    now = timezone.now()

    # Base Query: active sessions, enabled activity types, within radius
    qs = ActivitySession.objects.filter(
        status=ActivitySession.Status.ACTIVE,
        activity_type__is_active=True,
        location__distance_lte=(user_point, D(m=radius_m))
    ).annotate(
        distance_geo=Distance('location', user_point),
        active_participant_count=Count(
            'participations',
            filter=Q(participations__status=Participation.Status.ACTIVE)
        )
    ).filter(
        active_participant_count__gt=0
    ).select_related('activity_type', 'created_by')

    if activity_slug:
        qs = qs.filter(activity_type__slug=activity_slug)

    # Privacy filtering: omit sessions where creator has HIDDEN privacy, unless request user is owner
    if user and user.is_authenticated:
        qs = qs.filter(Q(created_by=user) | ~Q(created_by__location_privacy_mode='hidden'))
    else:
        qs = qs.exclude(created_by__location_privacy_mode='hidden')

    # Fetch currently live Gravity Events for XP bonus indicators
    live_events = list(GravityEvent.objects.filter(
        is_active=True,
        starts_at__lte=now,
        ends_at__gt=now
    ).select_related('activity_type', 'badge'))

    # Check if requesting user is already active in a session
    user_active_session_id = None
    if user and user.is_authenticated:
        active_part = Participation.objects.filter(
            user=user,
            status=Participation.Status.ACTIVE
        ).values_list('session_id', flat=True).first()
        user_active_session_id = active_part

    items = []
    for session in qs:
        is_owner = (user and user.is_authenticated and session.created_by_id == user.id)
        privacy_mode = getattr(session.created_by, 'location_privacy_mode', 'blurred')

        raw_dist = session.distance_geo.m if hasattr(session, 'distance_geo') and session.distance_geo else 0.0
        active_count = session.active_participant_count
        started_at = session.created_at

        score = compute_pulse_score(
            distance_m=raw_dist,
            participant_count=active_count,
            started_at=started_at,
            now=now,
            radius_m=radius_m
        )

        dist_display = format_privacy_safe_distance(
            distance_m=raw_dist,
            privacy_mode=privacy_mode,
            is_owner=is_owner
        )

        # Match live event
        event_data = None
        matching_events = [
            ev for ev in live_events
            if ev.activity_type is None or ev.activity_type_id == session.activity_type_id
        ]
        if matching_events:
            best_event = max(matching_events, key=lambda e: (e.xp_multiplier, e.flat_xp_bonus))
            event_data = {
                "id": best_event.id,
                "name": best_event.name,
                "xp_multiplier": float(best_event.xp_multiplier),
                "flat_xp_bonus": best_event.flat_xp_bonus,
                "badge_icon": best_event.badge.icon if best_event.badge else None
            }

        # can_join: user can join if authenticated and not already in an active session
        can_join = True
        if not user or not user.is_authenticated:
            can_join = False
        elif user_active_session_id is not None:
            # User is already active in this or another session
            can_join = False

        items.append({
            "session_id": str(session.id),
            "activity": {
                "slug": session.activity_type.slug,
                "name": session.activity_type.name,
                "icon": session.activity_type.icon,
                "color": session.activity_type.color
            },
            "label": session.label if session.label else None,
            "participant_count": active_count,
            "started_at": started_at.isoformat(),
            "distance": {
                "display": dist_display
            },
            "pulse_score": score,
            "can_join": can_join,
            "event": event_data,
            # Internal fields for secondary tie-breaking (popped before returning)
            "_raw_dist": raw_dist,
            "_started_ts": started_at.timestamp()
        })

    # Deterministic ordering:
    # 1. pulse_score descending
    # 2. participant_count descending
    # 3. raw_dist ascending (shorter distance)
    # 4. started_ts descending (newer session)
    # 5. session_id ascending (stable string UUID)
    items.sort(key=lambda x: (
        -x['pulse_score'],
        -x['participant_count'],
        x['_raw_dist'],
        -x['_started_ts'],
        x['session_id']
    ))

    # Apply limit
    items = items[:limit]

    # Clean internal sort fields
    for item in items:
        item.pop('_raw_dist', None)
        item.pop('_started_ts', None)

    return {
        "items": items,
        "search_radius_m": radius_m
    }
