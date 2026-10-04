from django.db import transaction
from django.utils import timezone
from activities.models import Season, SeasonStanding, SeasonRewardRule, SeasonRewardAward, XPTransaction, ActivityType
from .xp_service import award_xp
from .badge_service import award_badge

def get_current_season():
    now = timezone.now()
    return Season.objects.filter(
        is_enabled=True,
        starts_at__lte=now,
        ends_at__gt=now
    ).first()

@transaction.atomic
def finalize_season(season_slug):
    season = Season.objects.get(slug=season_slug)
    
    if season.finalized_at:
        return {"status": "already_finalized", "season": season.name}
    
    # We allow finalization only if ended (or we force it for dev, but let's strictly require it unless overriden)
    now = timezone.now()
    if season.ends_at > now:
        # Prevent premature finalization
        raise ValueError("Cannot finalize a season that has not yet ended.")
        
    from .leaderboard_service import compute_leaderboard
    
    activities = ActivityType.objects.filter(is_active=True)
    standings_created = 0
    rewards_issued = 0
    
    from .leaderboard_service import compute_leaderboard
    
    activities = ActivityType.objects.filter(is_active=True)
    standings_created = 0
    rewards_issued = 0
    
    for activity in activities:
        primary_metric, rows = compute_leaderboard(activity, period='season', target_season=season)
        if not primary_metric or not rows:
            continue
            
        for row in rows:
            user_id = row['user']['id']
            rank = row['rank']
            value = row['value']
            
            # Create Standing
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Check for existing to be idempotent
            standing, created = SeasonStanding.objects.get_or_create(
                season=season,
                activity_type=activity,
                user=user,
                defaults={
                    'rank': rank,
                    'metric_name': primary_metric.name,
                    'value': value
                }
            )
            if created:
                standings_created += 1

            # Process Rewards
            rules = SeasonRewardRule.objects.filter(season=season, min_rank__lte=rank, max_rank__gte=rank)
            for rule in rules:
                if rule.activity_type and rule.activity_type != activity:
                    continue # Skip if rule specifies different activity
                    
                # Create award idempotently
                award, a_created = SeasonRewardAward.objects.get_or_create(
                    season=season,
                    rule=rule,
                    user=user,
                    activity_type=activity,
                    defaults={
                        'xp_awarded': rule.xp_bonus,
                        'badge_awarded': rule.badge is not None
                    }
                )
                
                if a_created:
                    rewards_issued += 1
                    if rule.xp_bonus > 0:
                        award_xp(
                            user=user,
                            amount=rule.xp_bonus,
                            reason=XPTransaction.Reason.SEASON,
                            description=f"Season Reward: {season.name} {activity.name} Rank {rank}",
                            activity_type=activity
                        )
                    if rule.badge:
                        award_badge(user, rule.badge.slug, activity_type=activity)
                        
    season.finalized_at = timezone.now()
    season.save(update_fields=['finalized_at'])
    
    return {
        "status": "success",
        "season": season.name,
        "standings_created": standings_created,
        "rewards_issued": rewards_issued
    }
