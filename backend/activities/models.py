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
