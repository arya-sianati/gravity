import math
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from activities.models import XPTransaction, Participation

def level_for_xp(xp: int) -> int:
    """
    Curve: Level = (-1 + sqrt(9 + 0.16 * xp)) / 2
    L1: 0, L2: 100, L3: 250, L4: 450, L5: 700...
    """
    if xp <= 0:
        return 1
    # Floating point precision safe for reasonable XP ranges
    val = (-1.0 + math.sqrt(9.0 + 0.16 * xp)) / 2.0
    return max(1, math.floor(val))

def xp_for_level(level: int) -> int:
    """
    Curve: XP = 25 * (L^2 + L - 2)
    """
    if level <= 1:
        return 0
    return 25 * (level * level + level - 2)

def xp_for_next_level(level: int) -> int:
    return xp_for_level(level + 1)

@transaction.atomic
def award_xp(user, amount: int, reason: str, description: str = '', participation=None, activity_type=None):
    if amount == 0:
        return None
        
    # Idempotency check if participation is given
    if participation:
        if XPTransaction.objects.filter(participation=participation, reason=reason).exists():
            return None # Already awarded

    xpt = XPTransaction.objects.create(
        user=user,
        amount=amount,
        reason=reason,
        description=description,
        participation=participation,
        activity_type=activity_type
    )

    # Recompute total
    # According to spec, sum(ledger) and cached should be consistent.
    from django.db.models import Sum
    total = XPTransaction.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Do not let total fall below 0
    total = max(0, total)
    
    user.total_xp = total
    user.current_level = level_for_xp(total)
    user.save(update_fields=['total_xp', 'current_level'])
    
    return xpt
