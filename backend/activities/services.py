from django.contrib.gis.geos import Point
from .models import Participation
from .logic.privacy_service import resolve_location_visibility, generalize_location, Visibility

def get_privacy_safe_feature(session, request_user=None):
    """
    Returns a GeoJSON Feature dict for the given session, applying central privacy rules.
    Returns None if the session should be completely hidden.
    """
    visibility = resolve_location_visibility(session.created_by, request_user)
    if visibility == Visibility.HIDDEN:
        return None
    elif visibility == Visibility.EXACT:
        location = session.location
    else: # BLURRED
        location = generalize_location(session.location)

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
