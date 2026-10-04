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
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Participation
        fields = ['id', 'user', 'status', 'joined_at', 'join_method', 'metrics']

    def get_metrics(self, obj):
        # We can optimize this later with prefetch_related, but for now this works.
        from .models import MetricValue
        return {mv.metric.slug: mv.value for mv in obj.metric_values.all()}

class ActivitySessionSerializer(serializers.ModelSerializer):
    activity_type_details = ActivityTypeSerializer(source='activity_type', read_only=True)
    created_by = ParticipantUserSerializer(read_only=True)
    active_participants_count = serializers.SerializerMethodField()
    my_participation = serializers.SerializerMethodField()

    class Meta:
        model = ActivitySession
        fields = [
            'id', 'activity_type', 'activity_type_details', 'created_by',
            'status', 'label', 'started_at', 'ended_at',
            'active_participants_count', 'my_participation'
        ]

    def get_active_participants_count(self, obj):
        return obj.participations.filter(status=Participation.Status.ACTIVE).count()
        
    def get_my_participation(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        from .models import Participation
        part = obj.participations.filter(user=request.user, status=Participation.Status.ACTIVE).first()
        if part:
            return ParticipationSerializer(part).data
        return None

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

class MetricValueSerializer(serializers.ModelSerializer):
    metric_slug = serializers.CharField(source='metric.slug', read_only=True)
    class Meta:
        from .models import MetricValue
        model = MetricValue
        fields = ['metric_slug', 'value', 'updated_at']


from .models import FriendChallenge, ChallengeParticipant

class ChallengeParticipantSerializer(serializers.ModelSerializer):
    user = ParticipantUserSerializer(read_only=True)

    class Meta:
        model = ChallengeParticipant
        fields = [
            'id',
            'user',
            'invitation_status',
            'joined_at',
            'progress',
            'is_winner',
            'rank',
        ]


class FriendChallengeSerializer(serializers.ModelSerializer):
    created_by = ParticipantUserSerializer(read_only=True)
    activity_type = ActivityTypeSerializer(read_only=True)
    metric = ActivityMetricSerializer(read_only=True)
    winner = ParticipantUserSerializer(read_only=True)
    participants = ChallengeParticipantSerializer(many=True, read_only=True)
    my_participant_info = serializers.SerializerMethodField()
    combined_progress = serializers.SerializerMethodField()

    class Meta:
        model = FriendChallenge
        fields = [
            'id',
            'title',
            'created_by',
            'activity_type',
            'metric',
            'challenge_type',
            'target_value',
            'starts_at',
            'ends_at',
            'status',
            'winner',
            'completed_at',
            'created_at',
            'updated_at',
            'participants',
            'my_participant_info',
            'combined_progress',
        ]

    def get_my_participant_info(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        part = obj.participants.filter(user=request.user).first()
        if part:
            return ChallengeParticipantSerializer(part).data
        return None

    def get_combined_progress(self, obj):
        if obj.challenge_type == FriendChallenge.ChallengeType.COOPERATIVE_TARGET:
            accepted = obj.participants.filter(invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED)
            return round(sum(p.progress for p in accepted), 2)
        return None


class ChallengeCreateSerializer(serializers.Serializer):
    activity_type_slug = serializers.CharField(required=False)
    activity_type = serializers.CharField(required=False)
    metric_slug = serializers.CharField(required=False)
    metric = serializers.CharField(required=False)
    challenge_type = serializers.ChoiceField(choices=FriendChallenge.ChallengeType.choices)
    target_value = serializers.FloatField(required=False, allow_null=True)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    invitees = serializers.ListField(child=serializers.IntegerField(), required=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=150)
