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

from .models import ActivitySession, Participation
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer, GeometryField

User = get_user_model()

class ParticipantUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

class ParticipationSerializer(serializers.ModelSerializer):
    user = ParticipantUserSerializer(read_only=True)

    class Meta:
        model = Participation
        fields = ['id', 'user', 'status', 'joined_at', 'join_method']

class ActivitySessionSerializer(serializers.ModelSerializer):
    activity_type_details = ActivityTypeSerializer(source='activity_type', read_only=True)
    created_by = ParticipantUserSerializer(read_only=True)
    active_participants_count = serializers.SerializerMethodField()

    class Meta:
        model = ActivitySession
        fields = [
            'id', 'activity_type', 'activity_type_details', 'created_by',
            'status', 'label', 'started_at', 'ended_at',
            'active_participants_count'
        ]

    def get_active_participants_count(self, obj):
        return obj.participations.filter(status=Participation.Status.ACTIVE).count()

class ActivitySessionCreateSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True)
    lng = serializers.FloatField(write_only=True)

    class Meta:
        model = ActivitySession
        fields = ['activity_type', 'label', 'lat', 'lng']

class NearbySessionSerializer(serializers.ModelSerializer):
    activity_type_slug = serializers.CharField(source='activity_type.slug', read_only=True)
    active_participants_count = serializers.SerializerMethodField()
    distance_m = serializers.SerializerMethodField()

    class Meta:
        model = ActivitySession
        fields = ['id', 'activity_type_slug', 'status', 'started_at', 'active_participants_count', 'distance_m']

    def get_active_participants_count(self, obj):
        return obj.participations.filter(status=Participation.Status.ACTIVE).count()
        
    def get_distance_m(self, obj):
        # We'll annotate distance dynamically in the view
        if hasattr(obj, 'distance'):
            return getattr(obj, 'distance').m
        return None
