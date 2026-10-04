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

    # Auto-stop
    auto_stop_enabled = models.BooleanField(default=True)
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
    
    # Placeholders for future auto-stop & heartbeats
    outside_since = models.DateTimeField(null=True, blank=True)
    
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
