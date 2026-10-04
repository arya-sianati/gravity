from django.core.management.base import BaseCommand
from django.db import transaction
from activities.models import ActivityType, ActivityMetric

class Command(BaseCommand):
    help = 'Seeds the initial Activity Types and Metrics for Gravity'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Gravity Activities...")

        activities_data = [
            {
                'name': 'Basketball', 'slug': 'basketball', 'icon': '🏀', 'color': '#F59E0B',
                'description': 'Play a pickup game of basketball.',
                'sort_order': 10, 'cluster_radius_m': 200, 'join_suggestion_radius_m': 500,
                'metrics': [
                    {'name': 'Points', 'slug': 'points', 'data_type': ActivityMetric.DataType.INTEGER, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 1.0, 'sort_order': 10}
                ]
            },
            {
                'name': 'Running', 'slug': 'running', 'icon': '🏃', 'color': '#3B82F6',
                'description': 'Go for a run.',
                'sort_order': 20, 'gps_tracking_enabled': True,
                'metrics': [
                    {'name': 'Distance', 'slug': 'distance', 'unit': 'km', 'data_type': ActivityMetric.DataType.DECIMAL, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 2.0, 'sort_order': 10},
                    {'name': 'Duration', 'slug': 'duration', 'unit': 'min', 'data_type': ActivityMetric.DataType.DURATION, 'aggregation': ActivityMetric.AggregationMode.SUM, 'xp_weight': 1.0, 'sort_order': 20},
                ]
            },
            {
                'name': 'Gaming', 'slug': 'gaming', 'icon': '🎮', 'color': '#8B5CF6',
                'description': 'Play video games with others.',
                'sort_order': 30, 'qr_join_enabled': True,
                'metrics': [
                    {'name': 'Wins', 'slug': 'wins', 'data_type': ActivityMetric.DataType.INTEGER, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 3.0, 'sort_order': 10}
                ]
            },
            {
                'name': 'Studying', 'slug': 'studying', 'icon': '📚', 'color': '#10B981',
                'description': 'Study sessions.',
                'sort_order': 40, 'auto_stop_enabled': True,
                'metrics': [
                    {'name': 'Hours', 'slug': 'hours', 'unit': 'hr', 'data_type': ActivityMetric.DataType.DECIMAL, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 1.5, 'sort_order': 10}
                ]
            },
            {
                'name': 'Workout', 'slug': 'workout', 'icon': '💪', 'color': '#EF4444',
                'description': 'Gym and fitness workouts.',
                'sort_order': 50,
                'metrics': [
                    {'name': 'Calories', 'slug': 'calories', 'unit': 'kcal', 'data_type': ActivityMetric.DataType.INTEGER, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 0.1, 'sort_order': 10}
                ]
            },
            {
                'name': 'Soccer', 'slug': 'soccer', 'icon': '⚽', 'color': '#22C55E',
                'description': 'Play soccer.',
                'sort_order': 60,
                'metrics': [
                    {'name': 'Goals', 'slug': 'goals', 'data_type': ActivityMetric.DataType.INTEGER, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 5.0, 'sort_order': 10}
                ]
            },
            {
                'name': 'Other', 'slug': 'other', 'icon': '✨', 'color': '#6B7280',
                'description': 'Any other activity.',
                'sort_order': 999,
                'metrics': [
                    {'name': 'Duration', 'slug': 'duration', 'unit': 'min', 'data_type': ActivityMetric.DataType.DURATION, 'aggregation': ActivityMetric.AggregationMode.SUM, 'is_primary': True, 'xp_weight': 1.0, 'sort_order': 10}
                ]
            }
        ]

        with transaction.atomic():
            for act_data in activities_data:
                metrics_data = act_data.pop('metrics', [])
                
                # Fetch or create ActivityType
                activity, created = ActivityType.objects.update_or_create(
                    slug=act_data['slug'],
                    defaults=act_data
                )
                
                if created:
                    self.stdout.write(f"Created Activity: {activity.name}")
                else:
                    self.stdout.write(f"Updated Activity: {activity.name}")

                # Update or create metrics
                existing_metric_slugs = []
                for m_data in metrics_data:
                    metric_slug = m_data['slug']
                    existing_metric_slugs.append(metric_slug)
                    metric, m_created = ActivityMetric.objects.update_or_create(
                        activity_type=activity,
                        slug=metric_slug,
                        defaults=m_data
                    )
                    
                # Optionally, you can delete metrics that are no longer in the seed
                ActivityMetric.objects.filter(activity_type=activity).exclude(slug__in=existing_metric_slugs).delete()

        self.stdout.write(self.style.SUCCESS("Successfully seeded activities!"))
