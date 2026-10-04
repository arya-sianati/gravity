from django.core.management.base import BaseCommand
from activities.logic.season_service import finalize_season

class Command(BaseCommand):
    help = 'Finalizes a season and awards XP and badges'

    def add_arguments(self, parser):
        parser.add_argument('season_slug', type=str, help='The slug of the season to finalize')

    def handle(self, *args, **options):
        season_slug = options['season_slug']
        try:
            result = finalize_season(season_slug)
            if result.get("status") == "already_finalized":
                self.stdout.write(self.style.WARNING(f"Season '{season_slug}' is already finalized."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Season '{season_slug}' finalized successfully!"))
                self.stdout.write(f"Standings created: {result['standings_created']}")
                self.stdout.write(f"Rewards issued: {result['rewards_issued']}")
        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error finalizing season: {e}"))
