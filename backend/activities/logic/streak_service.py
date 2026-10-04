from django.utils import timezone
from activities.models import Streak

def get_current_date():
    return timezone.localtime(timezone.now()).date()

def get_effective_streak(streak_obj):
    if not streak_obj or not streak_obj.last_qualified_date:
        return 0
    
    current_date = get_current_date()
    delta = (current_date - streak_obj.last_qualified_date).days
    
    if delta > 1:
        return 0
    return streak_obj.current_count

def evaluate_streak(user, participation):
    """
    Evaluates streak after a valid participation completes.
    Returns (Streak, incremented_bool, newly_awarded_longest)
    """
    # Use timezone-aware completion time
    completed_date = timezone.localtime(participation.left_at or timezone.now()).date()
    
    streak, _ = Streak.objects.get_or_create(user=user)
    
    incremented = False
    new_longest = False
    
    if streak.last_qualified_date is None:
        streak.current_count = 1
        streak.last_qualified_date = completed_date
        incremented = True
    else:
        # Prevent future dates or duplicate processing
        if completed_date <= streak.last_qualified_date:
            pass # Already counted today, or out-of-order execution
        else:
            delta = (completed_date - streak.last_qualified_date).days
            if delta == 1:
                streak.current_count += 1
                incremented = True
            elif delta > 1:
                streak.current_count = 1
                incremented = True
            
            streak.last_qualified_date = completed_date
    
    if streak.current_count > streak.longest_count:
        streak.longest_count = streak.current_count
        new_longest = True
        
    streak.save()
    return streak, incremented, new_longest
