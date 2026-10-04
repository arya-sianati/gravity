from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.core.exceptions import ValidationError, PermissionDenied

from accounts.models import User
from activities.models import (
    ActivityType,
    ActivitySession,
    Participation,
    MetricValue,
    ActivityMetric,
    XPTransaction,
)


@transaction.atomic
def finalize_participation(
    participation_id: int,
    left_status=Participation.Status.LEFT,
    left_time: datetime = None,
    user: User = None
) -> dict:
    """
    Authoritative, idempotent lifecycle termination for a Participation.
    Used by both manual leave and automated auto-stop.
    """
    if left_time is None:
        left_time = timezone.now()

    qs = Participation.objects.select_for_update().select_related(
        'session',
        'session__activity_type',
        'user'
    )
    if user:
        qs = qs.filter(user=user)

    try:
        participation = qs.get(id=participation_id)
    except Participation.DoesNotExist:
        return {"error": "Participation not found"}

    # Concurrency check: If already concluded, do NOT transition or reward again
    if participation.status != Participation.Status.ACTIVE:
        return {
            "already_concluded": True,
            "status": participation.status,
            "left_at": participation.left_at
        }

    session = participation.session
    activity_type = session.activity_type
    target_user = participation.user

    participation.status = left_status
    participation.left_at = left_time

    # Auto-calculate duration metrics
    duration_seconds = max(0.0, (participation.left_at - participation.joined_at).total_seconds())
    duration_metrics = activity_type.metrics.filter(data_type=ActivityMetric.DataType.DURATION)
    for metric in duration_metrics:
        val = duration_seconds
        if metric.unit and 'min' in metric.unit.lower():
            val = duration_seconds / 60.0
        elif metric.unit and 'hour' in metric.unit.lower():
            val = duration_seconds / 3600.0

        MetricValue.objects.update_or_create(
            participation=participation,
            metric=metric,
            defaults={'value': val}
        )

    participation.save(update_fields=['status', 'left_at', 'updated_at'])

    # Progression evaluations (XP, Streaks, Badges, Events)
    min_duration = getattr(settings, 'GRAVITY_MIN_XP_DURATION_SECONDS', 60)
    from activities.logic.xp_service import award_xp
    from activities.logic.streak_service import evaluate_streak
    from activities.logic.achievement_service import evaluate_after_participation
    from activities.logic.event_service import evaluate_events_for_participation

    xp_awarded = None
    level_up = False
    streak_state = None
    badges_earned = []
    events_awarded = []

    if duration_seconds >= min_duration:
        old_level = target_user.current_level
        desc = "Auto-stopped" if left_status == Participation.Status.AUTO_STOPPED else "Completed"
        xpt = award_xp(
            user=target_user,
            amount=activity_type.default_xp,
            reason='participation',
            description=f"{desc} {activity_type.name} participation",
            participation=participation,
            activity_type=activity_type
        )

        # Streak evaluation
        streak, incremented, _ = evaluate_streak(target_user, participation)
        streak_state = {
            "current": streak.current_count,
            "longest": streak.longest_count
        }

        # Badge evaluation
        earned_list = evaluate_after_participation(target_user, participation, streak)
        for b in earned_list:
            badges_earned.append({
                "slug": b.slug,
                "name": b.name,
                "icon": b.icon
            })

        # Event evaluation
        event_results = evaluate_events_for_participation(
            user=target_user,
            participation=participation,
            base_xp=activity_type.default_xp
        )
        if event_results:
            events_awarded = event_results

        if xpt:
            target_user.refresh_from_db()
            xp_awarded = xpt.amount
            if target_user.current_level > old_level:
                level_up = True

    # Challenge evaluation integration (Phase 17)
    try:
        from activities.models import FriendChallenge
        from activities.logic.challenge_service import calculate_and_update_challenge_progress
        active_challenges = FriendChallenge.objects.filter(
            participants__user=target_user,
            activity_type=activity_type,
            status__in=[FriendChallenge.Status.ACTIVE, FriendChallenge.Status.PENDING]
        ).distinct()
        for ch in active_challenges:
            try:
                calculate_and_update_challenge_progress(ch, now=left_time)
            except Exception:
                pass
    except Exception:
        pass

    # Session completion if final active participant left
    active_count = session.participations.filter(status=Participation.Status.ACTIVE).count()
    session_ended = False
    if active_count == 0 and session.status == ActivitySession.Status.ACTIVE:
        session.status = ActivitySession.Status.ENDED
        session.ended_at = left_time
        session.save(update_fields=['status', 'ended_at', 'updated_at'])
        session_ended = True

    detail_msg = (
        "Activity ended because you left the activity area."
        if left_status == Participation.Status.AUTO_STOPPED
        else "Successfully left the session."
    )

    return {
        "detail": detail_msg,
        "xp_awarded": xp_awarded,
        "level_up": level_up,
        "current_level": target_user.current_level,
        "streak": streak_state,
        "badges_earned": badges_earned,
        "events_awarded": events_awarded,
        "session_ended": session_ended,
        "participation_status": participation.status
    }


@transaction.atomic
def process_location_heartbeat(
    user: User,
    lat: float,
    lng: float,
    participation_id: int = None,
    now: datetime = None
) -> dict:
    """
    Validates coordinates, tracks location heartbeat, and executes anchor-radius
    auto-stop logic when a participant moves outside the activity boundary.
    """
    # 1. Coordinate Validation
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        raise ValidationError("Invalid coordinates format.")

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        raise ValidationError("Coordinates out of valid planetary range.")

    if now is None:
        now = timezone.now()

    current_point = Point(lng, lat, srid=4326)

    # 2. Resolve Active Participation
    qs = Participation.objects.select_for_update().select_related(
        'session',
        'session__activity_type'
    )

    if participation_id:
        try:
            part = qs.get(id=participation_id)
        except Participation.DoesNotExist:
            raise ValidationError("Participation not found.")

        if part.user_id != user.id:
            raise PermissionDenied("You cannot submit a heartbeat for another user's participation.")

        if part.status != Participation.Status.ACTIVE:
            return {
                "participation_status": part.status,
                "inside_activity_area": False,
                "outside_since": part.outside_since.isoformat() if part.outside_since else None,
                "grace_remaining_seconds": 0,
                "auto_stopped": False,
                "already_concluded": True
            }
    else:
        part = qs.filter(user=user, status=Participation.Status.ACTIVE).first()
        if not part:
            raise ValidationError("No active participation found for this user.")

    session = part.session
    activity_type = session.activity_type

    # 3. Update heartbeat tracking fields
    part.last_heartbeat_at = now
    part.last_location = current_point

    # 4. Check Auto-Stop Mode Configuration
    is_anchor_mode = (
        activity_type.auto_stop_enabled and
        activity_type.auto_stop_mode == ActivityType.AutoStopMode.ANCHOR_RADIUS
    )

    if not is_anchor_mode:
        # Movement activities (e.g. Running) or auto-stop disabled
        part.outside_since = None
        part.save(update_fields=['last_heartbeat_at', 'last_location', 'outside_since', 'updated_at'])
        return {
            "participation_status": "active",
            "inside_activity_area": True,
            "outside_since": None,
            "grace_remaining_seconds": None,
            "auto_stopped": False
        }

    # 5. Exact PostGIS Anchor Distance Calculation
    session_with_dist = ActivitySession.objects.filter(id=session.id).annotate(
        d=Distance('location', current_point)
    ).first()

    distance_m = session_with_dist.d.m if session_with_dist and session_with_dist.d else 0.0

    # Requirement 29: Distance <= radius is inside; Distance > radius is outside
    is_inside = distance_m <= activity_type.auto_stop_radius_m

    if is_inside:
        # User is within allowed activity boundary -> clear grace state
        part.outside_since = None
        part.save(update_fields=['last_heartbeat_at', 'last_location', 'outside_since', 'updated_at'])
        return {
            "participation_status": "active",
            "inside_activity_area": True,
            "outside_since": None,
            "grace_remaining_seconds": None,
            "auto_stopped": False
        }

    # User is OUTSIDE allowed activity boundary
    if part.outside_since is None:
        part.outside_since = now

    grace_seconds = activity_type.auto_stop_grace_seconds
    elapsed = max(0.0, (now - part.outside_since).total_seconds())

    # Requirement 30: zero grace period triggers immediate auto-stop
    if elapsed >= grace_seconds or grace_seconds == 0:
        part.save(update_fields=['last_heartbeat_at', 'last_location', 'outside_since', 'updated_at'])

        completion = finalize_participation(
            participation_id=part.id,
            left_status=Participation.Status.AUTO_STOPPED,
            left_time=now,
            user=user
        )

        return {
            "participation_status": "auto_stopped",
            "inside_activity_area": False,
            "outside_since": part.outside_since.isoformat() if part.outside_since else None,
            "grace_remaining_seconds": 0,
            "auto_stopped": True,
            "completion": completion
        }

    # Still inside grace period
    remaining = max(0, int(grace_seconds - elapsed))
    part.save(update_fields=['last_heartbeat_at', 'last_location', 'outside_since', 'updated_at'])

    return {
        "participation_status": "active",
        "inside_activity_area": False,
        "outside_since": part.outside_since.isoformat(),
        "grace_remaining_seconds": remaining,
        "auto_stopped": False
    }
