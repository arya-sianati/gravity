from django.contrib.gis.geos import Point
from .models import Participation

def generalize_location(point: Point) -> Point:
    # Deterministic grid snapping for privacy
    # ~500m grid cell size = 0.005 degrees roughly
    cell_size = 0.005
    lat = round(point.y / cell_size) * cell_size
    lng = round(point.x / cell_size) * cell_size
    return Point(lng, lat, srid=4326)

def get_privacy_safe_feature(session, request_user=None):
    """
    Returns a GeoJSON Feature dict for the given session, applying privacy rules.
    Returns None if the session should be completely hidden.
    """
    owner = session.created_by
    privacy = owner.location_privacy_mode
    
    is_owner = (request_user == owner)
    
    # 1. Hidden
    if privacy == 'hidden' and not is_owner:
        return None
        
    # 2. Coordinate Resolution
    location = session.location
    if not is_owner:
        if privacy == 'blurred':
            location = generalize_location(session.location)
        elif privacy == 'friends':
            # Phase 07: Friends not fully implemented. Default to blurred.
            # When friends are implemented, check Friendship table here.
            location = generalize_location(session.location)
        elif privacy == 'exact':
            location = session.location
        elif privacy == 'hidden':
            # Covered above, but just in case
            return None

    # Calculate weight
    # active_count * ActivityType.heat_weight_multiplier
    # Since we use prefetch/annotate in the view, we should use session.active_count if available
    active_count = getattr(session, 'active_count', session.participations.filter(status=Participation.Status.ACTIVE).count())
    weight = active_count * session.activity_type.heat_weight_multiplier

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [location.x, location.y]
        },
        "properties": {
            "session_id": str(session.id),
            "activity_slug": session.activity_type.slug,
            "participant_count": active_count,
            "weight": float(weight)
        }
    }
