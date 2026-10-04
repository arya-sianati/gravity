from django.contrib.gis.geos import Point
from accounts.models import User, Friendship

METERS_TO_MILES = 0.000621371

class Visibility:
    HIDDEN = 'hidden'
    BLURRED = 'blurred'
    EXACT = 'exact'

def are_friends(user1, user2) -> bool:
    """
    Checks if two users have an accepted mutual friendship.
    """
    if not user1 or not user2:
        return False
    if not getattr(user1, 'is_authenticated', False) or not getattr(user2, 'is_authenticated', False):
        return False
    if user1.id == user2.id:
        return False
    try:
        return Friendship.are_friends(user1, user2)
    except Exception:
        return False

def resolve_location_visibility(owner, viewer, privacy_mode=None) -> str:
    """
    Authoritative single-source-of-truth privacy decision for:
    - Map (GeoJSON coordinates)
    - Pulse (Item inclusion and distance precision)
    - Session Detail (Location exposure)
    - Friends Presence (Distance / location presentation)

    Strict Matrix:
    - Hidden:
        owner -> exact
        friend -> hidden
        stranger -> hidden
    - Blurred:
        owner -> exact
        friend -> blurred
        stranger -> blurred
    - Friends:
        owner -> exact
        accepted friend -> exact
        pending user -> blurred
        former friend -> blurred
        stranger -> blurred
    - Exact:
        owner -> exact
        friend -> exact
        stranger -> exact

    Returns: 'hidden' | 'blurred' | 'exact'
    """
    if not owner:
        return Visibility.BLURRED

    # 1. Owner always sees their own exact location
    if viewer and getattr(viewer, 'is_authenticated', False) and viewer.id == owner.id:
        return Visibility.EXACT

    mode = privacy_mode or getattr(owner, 'location_privacy_mode', User.PrivacyMode.BLURRED)

    # 2. Hidden is strictly hidden from everyone except the owner
    if mode == User.PrivacyMode.HIDDEN or mode == 'hidden':
        return Visibility.HIDDEN

    # 3. Exact is public exact opt-in
    if mode == User.PrivacyMode.EXACT or mode == 'exact':
        return Visibility.EXACT

    # 4. Friends Only: accepted friends get exact, everyone else gets blurred
    if mode == User.PrivacyMode.FRIENDS or mode == 'friends':
        if are_friends(owner, viewer):
            return Visibility.EXACT
        return Visibility.BLURRED

    # 5. Blurred: everyone gets blurred
    if mode == User.PrivacyMode.BLURRED or mode == 'blurred':
        return Visibility.BLURRED

    return Visibility.BLURRED

def generalize_location(point: Point) -> Point:
    """
    Deterministic grid snapping for location privacy.
    ~500m grid cell size = 0.005 degrees roughly.
    """
    cell_size = 0.005
    lat = round(point.y / cell_size) * cell_size
    lng = round(point.x / cell_size) * cell_size
    return Point(lng, lat, srid=4326)
