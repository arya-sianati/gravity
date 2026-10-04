from django.contrib import admin
from .models import ActivityType, ActivityMetric

class ActivityMetricInline(admin.TabularInline):
    model = ActivityMetric
    extra = 0
    fields = ('name', 'slug', 'unit', 'data_type', 'aggregation', 'is_primary', 'leaderboard_enabled', 'required', 'min_value', 'max_value', 'xp_weight', 'sort_order')

@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'auto_stop_enabled', 'auto_stop_mode', 'sort_order', 'cluster_radius_m', 'updated_at')
    list_filter = ('is_active', 'auto_stop_enabled', 'auto_stop_mode', 'self_start_enabled', 'qr_join_enabled', 'gps_tracking_enabled')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ActivityMetricInline]
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'icon', 'color', 'description', 'is_active', 'sort_order')
        }),
        ('Geospatial / Session', {
            'fields': ('cluster_radius_m', 'join_suggestion_radius_m')
        }),
        ('Capabilities', {
            'fields': ('self_start_enabled', 'qr_join_enabled', 'gps_tracking_enabled')
        }),
        ('Auto-Stop', {
            'fields': ('auto_stop_enabled', 'auto_stop_mode', 'auto_stop_radius_m', 'auto_stop_grace_seconds')
        }),
        ('Scoring / Heatmap', {
            'fields': ('default_xp', 'heat_weight_multiplier')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

from .models import ActivitySession, Participation

class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 0
    readonly_fields = ('joined_at', 'left_at', 'outside_since', 'last_heartbeat_at')
    fields = ('user', 'status', 'join_method', 'outside_since', 'last_heartbeat_at', 'joined_at', 'left_at')

@admin.register(ActivitySession)
class ActivitySessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity_type', 'status', 'created_by', 'started_at', 'ended_at')
    list_filter = ('status', 'activity_type')
    search_fields = ('id', 'created_by__username', 'label')
    readonly_fields = ('started_at', 'ended_at', 'join_token', 'created_at', 'updated_at')
    inlines = [ParticipationInline]

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'status', 'join_method', 'outside_since', 'last_heartbeat_at', 'joined_at')
    list_filter = ('status', 'join_method')
    search_fields = ('user__username', 'session__id')
    readonly_fields = ('joined_at', 'left_at', 'outside_since', 'last_heartbeat_at', 'last_location', 'created_at', 'updated_at')

from .models import MetricValue

@admin.register(MetricValue)
class MetricValueAdmin(admin.ModelAdmin):
    list_display = ('id', 'participation', 'metric', 'value', 'updated_at')
    list_filter = ('metric__activity_type', 'metric')
    search_fields = ('participation__user__username', 'metric__name')
    readonly_fields = ('created_at', 'updated_at')

from .models import XPTransaction, Badge, UserBadge, Streak

@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'reason', 'created_at')
    list_filter = ('reason',)
    search_fields = ('user__username',)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'icon')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at', 'activity_type')
    list_filter = ('badge',)
    search_fields = ('user__username', 'badge__name')
    readonly_fields = ('user', 'badge', 'earned_at', 'activity_type', 'metadata')

@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_count', 'longest_count', 'last_qualified_date')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'longest_count')

from .models import GravityEvent, EventReward

@admin.register(GravityEvent)
class GravityEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'computed_status', 'starts_at', 'ends_at', 'activity_type', 'xp_multiplier')
    list_filter = ('is_active', 'activity_type')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('computed_status', 'created_at', 'updated_at')
    
@admin.register(EventReward)
class EventRewardAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'base_xp', 'multiplier_bonus_xp', 'flat_bonus_xp', 'awarded_at')
    list_filter = ('event',)
    search_fields = ('user__username', 'event__name')
    readonly_fields = ('user', 'event', 'participation', 'base_xp', 'multiplier_bonus_xp', 'flat_bonus_xp', 'awarded_at')

from .models import Season, SeasonStanding, SeasonRewardRule, SeasonRewardAward

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_enabled', 'computed_status', 'starts_at', 'ends_at', 'finalized_at')
    list_filter = ('is_enabled',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('finalized_at',)

@admin.register(SeasonStanding)
class SeasonStandingAdmin(admin.ModelAdmin):
    list_display = ('season', 'activity_type', 'user', 'rank', 'value')
    list_filter = ('season', 'activity_type')
    readonly_fields = ('season', 'activity_type', 'user', 'rank', 'metric_name', 'value', 'finalized_at')

@admin.register(SeasonRewardRule)
class SeasonRewardRuleAdmin(admin.ModelAdmin):
    list_display = ('season', 'activity_type', 'min_rank', 'max_rank', 'xp_bonus', 'badge')
    list_filter = ('season', 'activity_type')

@admin.register(SeasonRewardAward)
class SeasonRewardAwardAdmin(admin.ModelAdmin):
    list_display = ('season', 'user', 'activity_type', 'xp_awarded', 'badge_awarded', 'awarded_at')
    list_filter = ('season', 'activity_type')
    readonly_fields = ('season', 'rule', 'user', 'activity_type', 'xp_awarded', 'badge_awarded', 'awarded_at')
