from rest_framework import serializers
from .models import ActivityType, ActivityMetric

class ActivityMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityMetric
        fields = [
            'id', 'name', 'slug', 'unit', 'data_type', 'aggregation',
            'is_primary', 'leaderboard_enabled', 'required', 'min_value', 'max_value'
        ]

class ActivityTypeSerializer(serializers.ModelSerializer):
    metrics = ActivityMetricSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityType
        fields = [
            'id', 'name', 'slug', 'icon', 'color', 'description',
            'cluster_radius_m', 'qr_join_enabled', 'self_start_enabled',
            'gps_tracking_enabled', 'metrics'
        ]
