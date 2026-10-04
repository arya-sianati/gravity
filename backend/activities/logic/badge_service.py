from django.db import transaction
from django.db import IntegrityError
from activities.models import Badge, UserBadge

@transaction.atomic
def award_badge(user, badge_slug: str, activity_type=None, metadata=None):
    """
    Idempotent award of a badge.
    Returns (UserBadge, created).
    """
    try:
        badge = Badge.objects.get(slug=badge_slug, is_active=True)
    except Badge.DoesNotExist:
        return None, False

    try:
        user_badge, created = UserBadge.objects.get_or_create(
            user=user,
            badge=badge,
            defaults={
                'activity_type': activity_type,
                'metadata': metadata or {}
            }
        )
        return user_badge, created
    except IntegrityError:
        # Race condition fallback
        user_badge = UserBadge.objects.filter(user=user, badge=badge).first()
        return user_badge, False
