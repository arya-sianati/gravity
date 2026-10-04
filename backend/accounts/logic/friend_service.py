from django.db import transaction
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.utils import timezone

from accounts.models import User, Friendship
from activities.models import Participation, ActivitySession
from activities.logic.privacy_service import resolve_location_visibility, Visibility, METERS_TO_MILES

def get_canonical_pair(u1, u2):
    if u1.id == u2.id:
        raise ValueError("A user cannot friend themselves.")
    return (u1, u2) if u1.id < u2.id else (u2, u1)

def are_friends(user1, user2) -> bool:
    if not user1 or not user2 or not user1.is_authenticated or not user2.is_authenticated or user1.id == user2.id:
        return False
    u_low, u_high = get_canonical_pair(user1, user2)
    return Friendship.objects.filter(user_a=u_low, user_b=u_high, status=Friendship.Status.ACCEPTED).exists()

def get_friendship_status_between(user, other_user) -> str:
    """
    Returns friendship relationship status from the perspective of 'user':
    'self' | 'none' | 'pending_outgoing' | 'pending_incoming' | 'accepted' | 'blocked'
    """
    if not user or not other_user or not user.is_authenticated:
        return 'none'
    if user.id == other_user.id:
        return 'self'

    u_low, u_high = get_canonical_pair(user, other_user)
    f = Friendship.objects.filter(user_a=u_low, user_b=u_high).first()
    if not f:
        return 'none'

    if f.status == Friendship.Status.ACCEPTED:
        return 'accepted'
    elif f.status == Friendship.Status.PENDING:
        if f.initiated_by_id == user.id:
            return 'pending_outgoing'
        return 'pending_incoming'
    elif f.status == Friendship.Status.BLOCKED:
        return 'blocked'
    elif f.status == Friendship.Status.DECLINED:
        return 'none'

    return 'none'

@transaction.atomic
def request_friendship(sender, recipient):
    """
    Creates or updates a friendship request from sender to recipient.
    Handles reciprocal race conditions by auto-accepting.
    """
    if sender.id == recipient.id:
        raise ValueError("Cannot send a friend request to yourself.")

    u_low, u_high = get_canonical_pair(sender, recipient)

    f, created = Friendship.objects.select_for_update().get_or_create(
        user_a=u_low,
        user_b=u_high,
        defaults={
            'initiated_by': sender,
            'status': Friendship.Status.PENDING
        }
    )

    if created:
        return f, "requested"

    if f.status == Friendship.Status.ACCEPTED:
        return f, "already_friends"

    if f.status == Friendship.Status.PENDING:
        if f.initiated_by_id == sender.id:
            return f, "already_requested"
        else:
            # Reciprocal request! Both sent request -> auto-accept
            f.status = Friendship.Status.ACCEPTED
            f.save(update_fields=['status', 'updated_at'])
            return f, "accepted"

    if f.status == Friendship.Status.DECLINED:
        f.initiated_by = sender
        f.status = Friendship.Status.PENDING
        f.save(update_fields=['initiated_by', 'status', 'updated_at'])
        return f, "requested"

    if f.status == Friendship.Status.BLOCKED:
        if f.initiated_by_id == sender.id:
            # Unblock and request
            f.initiated_by = sender
            f.status = Friendship.Status.PENDING
            f.save(update_fields=['initiated_by', 'status', 'updated_at'])
            return f, "requested"
        else:
            raise PermissionDenied("User is not available.")

    return f, "requested"

@transaction.atomic
def accept_friendship(user, request_id):
    """
    Accepts an incoming friend request addressed to 'user'.
    """
    try:
        f = Friendship.objects.select_for_update().get(id=request_id, status=Friendship.Status.PENDING)
    except Friendship.DoesNotExist:
        raise ValueError("Friend request not found or no longer pending.")

    # Authorization: must be the recipient
    if f.initiated_by_id == user.id:
        raise PermissionDenied("You cannot accept your own outgoing friend request.")
    if f.user_a_id != user.id and f.user_b_id != user.id:
        raise PermissionDenied("You are not authorized to accept this friend request.")

    f.status = Friendship.Status.ACCEPTED
    f.save(update_fields=['status', 'updated_at'])
    return f

@transaction.atomic
def decline_friendship(user, request_id):
    """
    Declines an incoming friend request addressed to 'user'.
    """
    try:
        f = Friendship.objects.select_for_update().get(id=request_id, status=Friendship.Status.PENDING)
    except Friendship.DoesNotExist:
        raise ValueError("Friend request not found or no longer pending.")

    if f.initiated_by_id == user.id:
        raise PermissionDenied("You cannot decline your own outgoing request. Cancel it instead.")
    if f.user_a_id != user.id and f.user_b_id != user.id:
        raise PermissionDenied("You are not authorized to decline this friend request.")

    f.status = Friendship.Status.DECLINED
    f.save(update_fields=['status', 'updated_at'])
    return f

@transaction.atomic
def cancel_friendship_request(user, request_id):
    """
    Cancels an outgoing friend request initiated by 'user'.
    """
    try:
        f = Friendship.objects.select_for_update().get(id=request_id, status=Friendship.Status.PENDING)
    except Friendship.DoesNotExist:
        raise ValueError("Friend request not found or no longer pending.")

    if f.initiated_by_id != user.id:
        raise PermissionDenied("You can only cancel your own outgoing friend requests.")

    f.delete()
    return True

@transaction.atomic
def remove_friendship(user, other_user):
    """
    Removes an accepted friendship between user and other_user.
    """
    if user.id == other_user.id:
        raise ValueError("Cannot remove friendship with yourself.")

    u_low, u_high = get_canonical_pair(user, other_user)
    deleted_count, _ = Friendship.objects.filter(
        user_a=u_low,
        user_b=u_high,
        status=Friendship.Status.ACCEPTED
    ).delete()

    return deleted_count > 0

def get_friends_for_user(user):
    """
    Returns a list of User objects who are accepted friends with 'user'.
    """
    if not user or not user.is_authenticated:
        return []

    friendships = Friendship.objects.filter(
        Q(user_a=user) | Q(user_b=user),
        status=Friendship.Status.ACCEPTED
    ).select_related('user_a', 'user_b')

    friends = []
    for f in friendships:
        friend = f.user_b if f.user_a_id == user.id else f.user_a
        friends.append(friend)

    return friends

def get_incoming_requests_for_user(user):
    """
    Returns pending requests where 'user' is the recipient.
    """
    if not user or not user.is_authenticated:
        return Friendship.objects.none()

    return Friendship.objects.filter(
        Q(user_a=user) | Q(user_b=user),
        status=Friendship.Status.PENDING
    ).exclude(
        initiated_by=user
    ).select_related('initiated_by')

def get_outgoing_requests_for_user(user):
    """
    Returns pending requests where 'user' is the initiator.
    """
    if not user or not user.is_authenticated:
        return Friendship.objects.none()

    return Friendship.objects.filter(
        status=Friendship.Status.PENDING,
        initiated_by=user
    ).select_related('user_a', 'user_b')

def get_friends_presence(user, viewer_lat: float = None, viewer_lng: float = None):
    """
    Surfaces currently active live presence for accepted friends of 'user'.
    Applies the central privacy resolver to ensure no unauthorized coordinates or high-precision distances leak.
    """
    friends = get_friends_for_user(user)
    if not friends:
        return []

    friend_ids = [f.id for f in friends]
    friends_by_id = {f.id: f for f in friends}

    active_parts = Participation.objects.filter(
        user_id__in=friend_ids,
        status=Participation.Status.ACTIVE,
        session__status=ActivitySession.Status.ACTIVE,
        session__activity_type__is_active=True
    ).select_related('session', 'session__activity_type', 'user')

    viewer_point = None
    if viewer_lat is not None and viewer_lng is not None:
        try:
            viewer_point = Point(float(viewer_lng), float(viewer_lat), srid=4326)
            active_parts = active_parts.annotate(distance_geo=Distance('session__location', viewer_point))
        except Exception:
            viewer_point = None

    presence_list = []
    for part in active_parts:
        friend = friends_by_id.get(part.user_id)
        if not friend:
            continue

        session = part.session
        visibility = resolve_location_visibility(friend, user)

        # Distance & Location presentation
        location_display = None
        if visibility == Visibility.HIDDEN:
            location_display = "Location hidden"
        elif visibility == Visibility.EXACT:
            if viewer_point:
                if hasattr(part, 'distance_geo') and part.distance_geo:
                    dist_m = part.distance_geo.m
                else:
                    dist_m = session.location.distance(viewer_point) * 111319.5
                dist_mi = dist_m * METERS_TO_MILES
                if dist_mi < 0.1:
                    location_display = "<0.1 mi away"
                else:
                    location_display = f"{dist_mi:.1f} mi away"
            else:
                location_display = "Exact location visible"
        else: # BLURRED
            if viewer_point:
                if hasattr(part, 'distance_geo') and part.distance_geo:
                    dist_m = part.distance_geo.m
                else:
                    dist_m = session.location.distance(viewer_point) * 111319.5
                dist_mi = dist_m * METERS_TO_MILES
                if dist_m < 400:
                    location_display = "Nearby"
                elif dist_m < 800:
                    location_display = "<0.5 mi away"
                elif dist_m < 1600:
                    location_display = "~1 mi away"
                else:
                    rounded = round(dist_mi * 2.0) / 2.0
                    location_display = f"~{rounded:.1f} mi away"
            else:
                location_display = "Approximate area"

        presence_list.append({
            "friend": {
                "id": friend.id,
                "username": friend.username,
                "display_name": friend.display_name or friend.username,
                "current_level": friend.current_level,
                "avatar_url": None
            },
            "session_id": str(session.id),
            "activity": {
                "slug": session.activity_type.slug,
                "name": session.activity_type.name,
                "icon": session.activity_type.icon,
                "color": session.activity_type.color
            },
            "label": session.label if session.label else None,
            "started_at": part.joined_at.isoformat() if part.joined_at else session.created_at.isoformat(),
            "location_display": location_display,
            "visibility_mode": visibility
        })

    return presence_list
