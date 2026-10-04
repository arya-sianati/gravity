from django.db.models import Count
from activities.models import Participation
from .badge_service import award_badge

def evaluate_after_participation(user, participation, streak_obj):
    """
    Evaluates badges that are triggered dynamically after a completion.
    """
    earned = []

    # 1. First Pull / Getting Started
    completed_participations = Participation.objects.filter(
        user=user, 
        status__in=[Participation.Status.COMPLETED, Participation.Status.LEFT, Participation.Status.AUTO_STOPPED]
    ).exclude(left_at__isnull=True) # Ensure it has a completion time
    
    # We use count() here which is safe for V1. Can be optimized later.
    total_count = completed_participations.count()
    
    if total_count >= 1:
        ub, created = award_badge(user, 'first-pull')
        if created: earned.append(ub.badge)
        
    if total_count >= 5:
        ub, created = award_badge(user, 'getting-started')
        if created: earned.append(ub.badge)

    # 2. Consistency / Streaks
    if streak_obj:
        if streak_obj.longest_count >= 7:
            ub, created = award_badge(user, 'consistent')
            if created: earned.append(ub.badge)
            
        if streak_obj.longest_count >= 30:
            ub, created = award_badge(user, 'on-fire')
            if created: earned.append(ub.badge)

    # 3. Explorer / Regular
    # Aggregate distinct activities
    activity_counts = completed_participations.values('session__activity_type').annotate(c=Count('id'))
    
    if len(activity_counts) >= 3:
        ub, created = award_badge(user, 'explorer')
        if created: earned.append(ub.badge)
        
    # Check if any single activity has >= 10 completions
    for item in activity_counts:
        if item['c'] >= 10:
            ub, created = award_badge(user, 'regular')
            if created: earned.append(ub.badge)
            break
            
    return earned
