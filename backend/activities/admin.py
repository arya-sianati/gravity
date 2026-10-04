from django.contrib import admin
from .models import ActivityType, ActivityMetric

class ActivityMetricInline(admin.TabularInline):
    model = ActivityMetric
    extra = 0
    fields = ('name', 'slug', 'unit', 'data_type', 'aggregation', 'is_primary', 'leaderboard_enabled', 'required', 'min_value', 'max_value', 'xp_weight', 'sort_order')

@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'sort_order', 'cluster_radius_m', 'updated_at')
    list_filter = ('is_active', 'self_start_enabled', 'qr_join_enabled', 'gps_tracking_enabled')
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
            'fields': ('auto_stop_enabled', 'auto_stop_radius_m', 'auto_stop_grace_seconds')
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
    readonly_fields = ('joined_at', 'left_at')
    fields = ('user', 'status', 'join_method', 'joined_at', 'left_at')

@admin.register(ActivitySession)
class ActivitySessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity_type', 'status', 'created_by', 'started_at', 'ended_at')
    list_filter = ('status', 'activity_type')
    search_fields = ('id', 'created_by__username', 'label')
    readonly_fields = ('started_at', 'ended_at', 'join_token', 'created_at', 'updated_at')
    inlines = [ParticipationInline]

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'status', 'join_method', 'joined_at')
    list_filter = ('status', 'join_method')
    search_fields = ('user__username', 'session__id')
    readonly_fields = ('joined_at', 'left_at', 'created_at', 'updated_at')
