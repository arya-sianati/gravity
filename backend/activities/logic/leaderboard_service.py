from django.db.models import Sum, Max, Avg, F
from django.utils import timezone
from datetime import timedelta
from activities.models import Participation, ActivityMetric, Season, SeasonStanding

def compute_leaderboard(activity_type, period='all', target_season=None):
    """
    Computes leaderboard rows for an activity type.
    Returns: (primary_metric, rows)
    """
    primary_metric = activity_type.metrics.filter(is_primary=True, leaderboard_enabled=True).first()
    if not primary_metric:
        primary_metric = activity_type.metrics.filter(leaderboard_enabled=True).first()
        
    if not primary_metric:
        return None, []
        
    now = timezone.now()
    qs = Participation.objects.filter(
        session__activity_type=activity_type,
        status__in=[Participation.Status.COMPLETED, Participation.Status.LEFT, Participation.Status.AUTO_STOPPED],
        metric_values__metric=primary_metric
    )

    if period == 'season' and target_season:
        # Filter by season boundaries
        qs = qs.filter(joined_at__gte=target_season.starts_at, joined_at__lt=target_season.ends_at)
    elif period == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        qs = qs.filter(joined_at__gte=start_of_day)
    elif period == 'week':
        start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        qs = qs.filter(joined_at__gte=start_of_week)
        
    agg_func = Sum
    if primary_metric.aggregation == ActivityMetric.AggregationMode.MAX:
        agg_func = Max
    elif primary_metric.aggregation == ActivityMetric.AggregationMode.AVERAGE:
        agg_func = Avg
        
    # Standard group by
    aggregated = qs.values(
        'user__id', 'user__username', 'user__display_name'
    ).annotate(
        total_val=agg_func('metric_values__value')
    ).order_by() # clear default ordering
    
    res = list(aggregated)
    res.sort(key=lambda x: x['total_val'], reverse=True)
        
    # Competition ranking (1, 1, 3)
    rows = []
    current_rank = 1
    previous_val = None
    tied_count = 0
    
    for idx, item in enumerate(res):
        val = item['total_val']
        if previous_val is None:
            rank = 1
        elif val == previous_val:
            rank = current_rank
            tied_count += 1
        else:
            rank = current_rank + tied_count + 1
            current_rank = rank
            tied_count = 0
            
        previous_val = val
        
        rows.append({
            "user": {
                "id": item['user__id'],
                "username": item['user__username'],
                "display_name": item['user__display_name'] or item['user__username'],
                "avatar_url": None
            },
            "rank": rank,
            "value": val
        })
        
    return primary_metric, rows
