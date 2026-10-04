from django.db import transaction
from django.utils import timezone
from activities.models import GravityEvent, EventReward, XPTransaction
from .badge_service import award_badge

def get_eligible_events(participation):
    """
    Returns a list of GravityEvents that the participation qualifies for.
    Rule: Participation must have STARTED during the event's active time window.
    """
    if not participation.joined_at:
        return []
    
    events = GravityEvent.objects.filter(
        is_active=True,
        starts_at__lte=participation.joined_at,
        ends_at__gt=participation.joined_at
    )
    
    eligible = []
    for ev in events:
        if ev.activity_type is None or ev.activity_type == participation.session.activity_type:
            eligible.append(ev)
            
    return eligible

@transaction.atomic
def evaluate_events_for_participation(user, participation, base_xp):
    """
    Evaluates events and issues EventRewards, XP, and Badges.
    Returns a list of reward dicts for the frontend.
    """
    eligible_events = get_eligible_events(participation)
    if not eligible_events:
        return []

    # Filter out events already rewarded for this participation
    already_rewarded_event_ids = set(
        EventReward.objects.filter(participation=participation).values_list('event_id', flat=True)
    )
    
    events_to_process = [ev for ev in eligible_events if ev.id not in already_rewarded_event_ids]
    if not events_to_process:
        return []

    # Calculate max multiplier
    max_multiplier = 1.0
    max_multiplier_event = None
    
    for ev in events_to_process:
        if ev.xp_multiplier > max_multiplier:
            max_multiplier = ev.xp_multiplier
            max_multiplier_event = ev

    # We only apply the max multiplier once across all events.
    # To be safe and predictable, we attach the multiplier bonus entirely to max_multiplier_event
    
    results = []
    combined_bonus_xp = 0
    event_names = []
    
    for ev in events_to_process:
        multiplier_bonus = 0
        if ev == max_multiplier_event and max_multiplier > 1.0:
            multiplier_bonus = int(base_xp * (max_multiplier - 1.0))
            
        flat_bonus = ev.flat_xp_bonus
        
        total_bonus = multiplier_bonus + flat_bonus
        combined_bonus_xp += total_bonus
        event_names.append(ev.name)
        
        # 1. Create EventReward (Idempotency ledger)
        reward = EventReward.objects.create(
            event=ev,
            user=user,
            participation=participation,
            base_xp=base_xp,
            multiplier_bonus_xp=multiplier_bonus,
            flat_bonus_xp=flat_bonus
        )
            
        # 2. Issue Badge if any
        badge_earned = None
        if ev.badge and ev.badge.is_active:
            ub, created = award_badge(user, ev.badge.slug, activity_type=ev.activity_type)
            if created:
                badge_earned = {
                    "slug": ev.badge.slug,
                    "name": ev.badge.name,
                    "icon": ev.badge.icon
                }
                
        results.append({
            "event": ev.name,
            "bonus_xp": total_bonus,
            "badge": badge_earned,
            "event_obj": ev
        })

    if combined_bonus_xp > 0:
        from .xp_service import award_xp
        award_xp(
            user=user,
            amount=combined_bonus_xp,
            reason=XPTransaction.Reason.EVENT,
            description=f"Event Bonus: {', '.join(event_names)}",
            participation=participation
        )

    return results

