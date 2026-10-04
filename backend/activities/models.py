from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class ActivityType(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=20, help_text="Emoji or icon identifier")
    color = models.CharField(max_length=20, help_text="Hex color code (e.g., #FF5733)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    # Geospatial/session configuration
    cluster_radius_m = models.FloatField(
        default=200.0,
        validators=[MinValueValidator(0.0)],
        help_text="Radius for visual clustering (meters)"
    )
    join_suggestion_radius_m = models.FloatField(
        default=500.0,
        validators=[MinValueValidator(0.0)],
        help_text="Radius for showing join suggestions (meters)"
    )

    # Capabilities
    self_start_enabled = models.BooleanField(default=True)
    qr_join_enabled = models.BooleanField(default=True)
    gps_tracking_enabled = models.BooleanField(default=False)

    class AutoStopMode(models.TextChoices):
        DISABLED = 'disabled', 'Disabled'
        ANCHOR_RADIUS = 'anchor_radius', 'Anchor Radius'
        INACTIVITY = 'inactivity', 'Inactivity'

    # Auto-stop
    auto_stop_enabled = models.BooleanField(default=True)
    auto_stop_mode = models.CharField(
        max_length=20,
        choices=AutoStopMode.choices,
        default=AutoStopMode.ANCHOR_RADIUS,
        help_text="Mode governing auto-stop behavior"
    )
    auto_stop_radius_m = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(0.0)],
        help_text="Distance threshold for auto-stop (meters)"
    )
    auto_stop_grace_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Time allowed outside radius before stopping"
    )

    # Scoring/map configuration
    default_xp = models.PositiveIntegerField(default=10)
    heat_weight_multiplier = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0)],
        help_text="Multiplier for map heat visualization"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.auto_stop_enabled and self.auto_stop_mode == self.AutoStopMode.ANCHOR_RADIUS:
            if self.auto_stop_radius_m is None or self.auto_stop_radius_m <= 0:
                raise ValidationError({'auto_stop_radius_m': 'auto_stop_radius_m must be greater than 0 for anchor_radius mode.'})
            if self.auto_stop_grace_seconds is None or self.auto_stop_grace_seconds < 0:
                raise ValidationError({'auto_stop_grace_seconds': 'auto_stop_grace_seconds must be non-negative.'})

class ActivityMetric(models.Model):
    class DataType(models.TextChoices):
        INTEGER = 'integer', 'Integer'
        DECIMAL = 'decimal', 'Decimal'
        DURATION = 'duration', 'Duration'
        BOOLEAN = 'boolean', 'Boolean'

    class AggregationMode(models.TextChoices):
        SUM = 'sum', 'Sum'
        MAX = 'max', 'Max'
        AVERAGE = 'average', 'Average'
        LATEST = 'latest', 'Latest'

    activity_type = models.ForeignKey(ActivityType, related_name='metrics', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    unit = models.CharField(max_length=50, blank=True)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.INTEGER)
    aggregation = models.CharField(max_length=20, choices=AggregationMode.choices, default=AggregationMode.SUM)
    is_primary = models.BooleanField(default=False, help_text="Only one primary metric allowed per activity")
    leaderboard_enabled = models.BooleanField(default=True)
    required = models.BooleanField(default=False)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    xp_weight = models.FloatField(default=1.0, validators=[MinValueValidator(0.0)])
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['activity_type', 'slug'], name='unique_metric_slug_per_activity'),
            models.UniqueConstraint(fields=['activity_type'], condition=models.Q(is_primary=True), name='unique_primary_metric_per_activity')
        ]

    def clean(self):
        super().clean()
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValidationError({"min_value": "min_value cannot be greater than max_value."})

    def __str__(self):
        return f"{self.activity_type.name} - {self.name}"

import uuid
from django.contrib.gis.db import models as gis_models
from django.contrib.auth import get_user_model

User = get_user_model()

class ActivitySession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_type = models.ForeignKey(ActivityType, related_name='sessions', on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, related_name='created_sessions', on_delete=models.PROTECT)
    
    # Geographic anchor location (WGS84)
    location = gis_models.PointField(srid=4326)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    label = models.CharField(max_length=50, blank=True, null=True, help_text="Short label for 'Other' activity")
    
    join_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', 'activity_type']),
        ]

    def __str__(self):
        base = f"{self.activity_type.name} - {self.status}"
        return f"{base} ({self.label})" if self.label else base


class Participation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        LEFT = 'left', 'Left'
        AUTO_STOPPED = 'auto_stopped', 'Auto Stopped'

    class JoinMethod(models.TextChoices):
        SELF = 'self', 'Self'
        QR = 'qr', 'QR'
        MAP = 'map', 'Map'
        SUGGESTION = 'suggestion', 'Suggestion'
        INVITE = 'invite', 'Invite'

    session = models.ForeignKey(ActivitySession, related_name='participations', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='participations', on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    join_method = models.CharField(max_length=20, choices=JoinMethod.choices, default=JoinMethod.SELF)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-stop & heartbeats
    outside_since = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_location = gis_models.PointField(srid=4326, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='active'),
                name='unique_active_participation'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.session.activity_type.name} ({self.status})"

class MetricValue(models.Model):
    participation = models.ForeignKey(Participation, related_name='metric_values', on_delete=models.CASCADE)
    metric = models.ForeignKey(ActivityMetric, related_name='values', on_delete=models.CASCADE)
    value = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('participation', 'metric')
        
    def __str__(self):
        return f"{self.participation.user.username} - {self.metric.name}: {self.value}"
        
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.metric.activity_type_id != self.participation.session.activity_type_id:
            raise ValidationError({'metric': 'Metric does not belong to the activity type of this participation.'})
            
        if self.metric.min_value is not None and self.value < self.metric.min_value:
            raise ValidationError({'value': f"Value cannot be less than {self.metric.min_value}"})
            
        if self.metric.max_value is not None and self.value > self.metric.max_value:
            raise ValidationError({'value': f"Value cannot be more than {self.metric.max_value}"})
            
        if self.metric.data_type == ActivityMetric.DataType.INTEGER:
            if not float(self.value).is_integer():
                raise ValidationError({'value': 'Value must be an integer.'})
        elif self.metric.data_type == ActivityMetric.DataType.BOOLEAN:
            if self.value not in (0.0, 1.0):
                raise ValidationError({'value': 'Value must be boolean (0.0 or 1.0).'})

class XPTransaction(models.Model):
    class Reason(models.TextChoices):
        PARTICIPATION = 'participation', 'Participation'
        STREAK = 'streak', 'Streak'
        BADGE = 'badge', 'Badge'
        EVENT = 'event', 'Event'
        CHALLENGE = 'challenge', 'Challenge'
        SEASON = 'season', 'Season'
        ADMIN = 'admin', 'Admin'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    user = models.ForeignKey(User, related_name='xp_transactions', on_delete=models.CASCADE)
    amount = models.IntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.CharField(max_length=255, blank=True)
    
    activity_type = models.ForeignKey(ActivityType, null=True, blank=True, on_delete=models.SET_NULL)
    participation = models.ForeignKey('Participation', null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['participation', 'reason'],
                condition=models.Q(participation__isnull=False),
                name='unique_xp_per_participation_reason'
            )
        ]

    def __str__(self):
        return f"{self.user.username} {self.amount:+d} XP ({self.reason})"

class Badge(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50) # e.g. emoji or icon class
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, related_name='badges', on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    activity_type = models.ForeignKey('ActivityType', null=True, blank=True, on_delete=models.SET_NULL)
    earned_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'badge'], name='unique_user_badge')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class Streak(models.Model):
    user = models.OneToOneField(User, related_name='streak', on_delete=models.CASCADE)
    current_count = models.PositiveIntegerField(default=0)
    longest_count = models.PositiveIntegerField(default=0)
    last_qualified_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_count} (Longest: {self.longest_count})"

class GravityEvent(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True, null=True)
    
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    activity_type = models.ForeignKey(ActivityType, null=True, blank=True, on_delete=models.SET_NULL, related_name='events')
    
    xp_multiplier = models.FloatField(default=1.0)
    flat_xp_bonus = models.PositiveIntegerField(default=0)
    badge = models.ForeignKey('Badge', null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        
    @property
    def is_live(self):
        if not self.is_active:
            return False
        from django.utils import timezone
        now = timezone.now()
        return self.starts_at <= now < self.ends_at

    @property
    def computed_status(self):
        if not self.is_active:
            return 'disabled'
        from django.utils import timezone
        now = timezone.now()
        if now < self.starts_at:
            return 'upcoming'
        if now >= self.ends_at:
            return 'ended'
        return 'live'

class EventReward(models.Model):
    event = models.ForeignKey(GravityEvent, on_delete=models.CASCADE, related_name='rewards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_rewards')
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE, related_name='event_rewards')
    
    base_xp = models.PositiveIntegerField(default=0)
    multiplier_bonus_xp = models.PositiveIntegerField(default=0)
    flat_bonus_xp = models.PositiveIntegerField(default=0)
    
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event', 'participation'], name='unique_event_participation_reward')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.event.name} Reward"

class Season(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_enabled = models.BooleanField(default=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F('starts_at')),
                name='season_ends_after_start'
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.db.models import Q
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError("ends_at must be strictly after starts_at.")
        
        # Check overlapping enabled seasons
        if self.is_enabled:
            overlapping = Season.objects.filter(
                is_enabled=True,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("Overlapping enabled seasons are not allowed.")

    @property
    def computed_status(self):
        if not self.is_enabled:
            return 'disabled'
        from django.utils import timezone
        now = timezone.now()
        if now < self.starts_at:
            return 'upcoming'
        if now >= self.ends_at:
            return 'ended'
        return 'live'

    def __str__(self):
        return self.name

class SeasonStanding(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='standings')
    activity_type = models.ForeignKey('ActivityType', on_delete=models.CASCADE, related_name='season_standings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='season_standings')
    rank = models.PositiveIntegerField()
    metric_name = models.CharField(max_length=255)
    value = models.FloatField()
    finalized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['season', 'activity_type', 'user'], name='unique_season_standing')
        ]

class SeasonRewardRule(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='reward_rules')
    activity_type = models.ForeignKey('ActivityType', null=True, blank=True, on_delete=models.CASCADE, help_text="Leave blank to apply to all activities")
    min_rank = models.PositiveIntegerField(help_text="Inclusive minimum rank (e.g., 1)")
    max_rank = models.PositiveIntegerField(help_text="Inclusive maximum rank (e.g., 3)")
    xp_bonus = models.PositiveIntegerField(default=0)
    badge = models.ForeignKey('Badge', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        act = self.activity_type.name if self.activity_type else "All"
        return f"{self.season.name} | {act} | Rank {self.min_rank}-{self.max_rank}"

class SeasonRewardAward(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    rule = models.ForeignKey(SeasonRewardRule, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.ForeignKey('ActivityType', on_delete=models.CASCADE)
    xp_awarded = models.PositiveIntegerField(default=0)
    badge_awarded = models.BooleanField(default=False)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['season', 'rule', 'user', 'activity_type'], name='unique_season_reward_award')
        ]


# =============================================================================
# Phase 17: Friend Challenges
# =============================================================================

class FriendChallenge(models.Model):
    class ChallengeType(models.TextChoices):
        FIRST_TO_TARGET = 'first_to_target', 'First to Target'
        HIGHEST_BY_DEADLINE = 'highest_by_deadline', 'Highest Metric by Deadline'
        COOPERATIVE_TARGET = 'cooperative_target', 'Cooperative Combined Target'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    title = models.CharField(max_length=150, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_challenges')
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, related_name='challenges')
    metric = models.ForeignKey(ActivityMetric, on_delete=models.CASCADE, related_name='challenges')
    challenge_type = models.CharField(max_length=30, choices=ChallengeType.choices)
    target_value = models.FloatField(null=True, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    winner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='won_challenges')
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"{self.activity_type.name} Challenge ({self.challenge_type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError({'ends_at': 'ends_at must be strictly after starts_at.'})
        if self.metric_id and self.activity_type_id and self.metric.activity_type_id != self.activity_type_id:
            raise ValidationError({'metric': 'Metric does not belong to the selected activity type.'})
        if self.challenge_type in [self.ChallengeType.FIRST_TO_TARGET, self.ChallengeType.COOPERATIVE_TARGET]:
            if self.target_value is None or self.target_value <= 0:
                raise ValidationError({'target_value': 'target_value must be greater than 0 for this challenge type.'})


class ChallengeParticipant(models.Model):
    class InvitationStatus(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    challenge = models.ForeignKey(FriendChallenge, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_participations')
    invitation_status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.INVITED)
    joined_at = models.DateTimeField(null=True, blank=True)
    progress = models.FloatField(default=0.0)
    is_winner = models.BooleanField(default=False)
    rank = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['challenge', 'user'], name='unique_challenge_participant')
        ]

    def __str__(self):
        return f"{self.user.username} in {self.challenge}"


class ChallengeReward(models.Model):
    class RewardType(models.TextChoices):
        COMPLETION = 'completion', 'Completion XP'
        WINNER = 'winner', 'Winner XP'

    challenge = models.ForeignKey(FriendChallenge, on_delete=models.CASCADE, related_name='rewards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_rewards')
    reward_type = models.CharField(max_length=20, choices=RewardType.choices)
    amount = models.PositiveIntegerField()
    xp_transaction = models.ForeignKey(XPTransaction, null=True, blank=True, on_delete=models.SET_NULL)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['challenge', 'user', 'reward_type'], name='unique_challenge_reward')
        ]

    def __str__(self):
        return f"{self.user.username} {self.reward_type} reward ({self.amount} XP)"
