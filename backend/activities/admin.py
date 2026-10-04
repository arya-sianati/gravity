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
