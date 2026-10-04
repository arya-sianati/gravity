from django.core.management.base import BaseCommand
from activities.models import Badge

class Command(BaseCommand):
    help = 'Seed initial Gravity badges safely.'

    def handle(self, *args, **options):
        initial_badges = [
            {
                'slug': 'first-pull',
                'name': 'First Pull',
                'description': 'Completed your first Gravity activity.',
                'icon': '🏅'
            },
            {
                'slug': 'getting-started',
                'name': 'Getting Started',
                'description': 'Completed 5 activities.',
                'icon': '🌱'
            },
            {
                'slug': 'consistent',
                'name': 'Consistent',
                'description': 'Maintained a 7-day activity streak.',
                'icon': '🔥'
            },
            {
                'slug': 'on-fire',
                'name': 'On Fire',
                'description': 'Maintained a 30-day activity streak.',
                'icon': '☄️'
            },
            {
                'slug': 'explorer',
                'name': 'Explorer',
                'description': 'Tried at least 3 different Activity Types.',
                'icon': '🧭'
            },
            {
                'slug': 'regular',
                'name': 'Regular',
                'description': 'Completed 10 activities of the same type.',
                'icon': '💪'
            }
        ]

        created_count = 0
        for b_data in initial_badges:
            obj, created = Badge.objects.get_or_create(
                slug=b_data['slug'],
                defaults={
                    'name': b_data['name'],
                    'description': b_data['description'],
                    'icon': b_data['icon']
                }
            )
            if created:
                created_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} new badges."))
