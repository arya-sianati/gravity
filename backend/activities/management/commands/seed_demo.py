from datetime import timedelta
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction

from accounts.models import User, Friendship
from activities.models import (
    ActivityType,
    ActivityMetric,
    ActivitySession,
    Participation,
    Badge,
    UserBadge,
    Streak,
    FriendChallenge,
    ChallengeParticipant,
    GravityEvent,
    Season,
    SeasonStanding,
)


class Command(BaseCommand):
    help = "Seeds comprehensive, idempotent demo data for MuleHacks 2026 presentation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clean existing demo records before reseeding",
        )
        parser.add_argument(
            "--lat",
            type=float,
            default=40.5985, # Default: Muhlenberg College campus, Allentown PA
            help="Center latitude for demo activities (default: 40.5985)",
        )
        parser.add_argument(
            "--lng",
            type=float,
            default=-75.5085, # Default: Muhlenberg College campus, Allentown PA
            help="Center longitude for demo activities (default: -75.5085)",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        center_lat = options["lat"]
        center_lng = options["lng"]
        now = timezone.now()

        self.stdout.write(f"=== Gravity Demo Seeder (Center: {center_lat}, {center_lng}) ===")

        DEMO_USERNAMES = ["demo_alex", "demo_jordan", "demo_sam", "demo_taylor"]
        DEMO_PASSWORD = "MuleHacks2026!"

        with transaction.atomic():
            if reset:
                self.stdout.write("Resetting demo data...")
                # Delete demo sessions
                ActivitySession.objects.filter(label__startswith="[Demo]").delete()
                # Delete demo challenges
                FriendChallenge.objects.filter(title__startswith="[Demo]").delete()
                # Delete demo events
                GravityEvent.objects.filter(slug="mulehacks-boost-2026").delete()
                # Delete demo seasons
                Season.objects.filter(slug="mulehacks-s1").delete()
                self.stdout.write("Cleaned previous demo sessions, challenges, events, and seasons.")

            # 1. Ensure Activities & Metrics
            pickleball, _ = ActivityType.objects.get_or_create(
                slug="pickleball",
                defaults={
                    "name": "Pickleball",
                    "icon": "🏓",
                    "color": "#10B981",
                    "description": "Fast-paced paddle sport.",
                    "sort_order": 25,
                    "cluster_radius_m": 150,
                    "auto_stop_enabled": True,
                    "auto_stop_mode": ActivityType.AutoStopMode.ANCHOR_RADIUS,
                    "auto_stop_radius_m": 100.0,
                    "auto_stop_grace_seconds": 300,
                },
            )
            ActivityMetric.objects.get_or_create(
                activity_type=pickleball,
                slug="wins",
                defaults={
                    "name": "Wins",
                    "data_type": ActivityMetric.DataType.INTEGER,
                    "aggregation": ActivityMetric.AggregationMode.SUM,
                    "is_primary": True,
                    "xp_weight": 5.0,
                    "leaderboard_enabled": True,
                },
            )

            basketball = ActivityType.objects.get(slug="basketball")
            studying = ActivityType.objects.get(slug="studying")
            running = ActivityType.objects.get(slug="running")
            workout = ActivityType.objects.get(slug="workout")

            # 2. Demo Users
            user_specs = [
                {
                    "username": "demo_alex",
                    "display_name": "Alex Rivera",
                    "email": "alex@gravity.college",
                    "level": 5,
                    "xp": 2150,
                    "privacy": User.PrivacyMode.FRIENDS,
                    "streak_current": 6,
                    "streak_longest": 10,
                    "badges": ["first-pull", "getting-started", "consistent"],
                },
                {
                    "username": "demo_jordan",
                    "display_name": "Jordan Lee",
                    "email": "jordan@gravity.college",
                    "level": 4,
                    "xp": 1480,
                    "privacy": User.PrivacyMode.BLURRED,
                    "streak_current": 4,
                    "streak_longest": 7,
                    "badges": ["first-pull", "explorer"],
                },
                {
                    "username": "demo_sam",
                    "display_name": "Sam Chen",
                    "email": "sam@gravity.college",
                    "level": 3,
                    "xp": 850,
                    "privacy": User.PrivacyMode.EXACT,
                    "streak_current": 2,
                    "streak_longest": 5,
                    "badges": ["first-pull"],
                },
                {
                    "username": "demo_taylor",
                    "display_name": "Taylor Kim",
                    "email": "taylor@gravity.college",
                    "level": 2,
                    "xp": 420,
                    "privacy": User.PrivacyMode.BLURRED,
                    "streak_current": 1,
                    "streak_longest": 3,
                    "badges": ["first-pull"],
                },
            ]

            users = {}
            for spec in user_specs:
                u, created = User.objects.get_or_create(username=spec["username"])
                u.display_name = spec["display_name"]
                u.email = spec["email"]
                u.current_level = spec["level"]
                u.total_xp = spec["xp"]
                u.location_privacy_mode = spec["privacy"]
                u.set_password(DEMO_PASSWORD)
                u.save()
                users[spec["username"]] = u

                # Set Streak
                Streak.objects.update_or_create(
                    user=u,
                    defaults={
                        "current_count": spec["streak_current"],
                        "longest_count": spec["streak_longest"],
                        "last_qualified_date": now.date(),
                    },
                )

                # Award Badges
                for b_slug in spec["badges"]:
                    try:
                        b = Badge.objects.get(slug=b_slug)
                        UserBadge.objects.get_or_create(user=u, badge=b)
                    except Badge.DoesNotExist:
                        pass

            self.stdout.write(f"Configured 4 demo users ({', '.join(DEMO_USERNAMES)}).")

            # 3. Friendships
            def make_friendship(u1, u2):
                a, b = (u1, u2) if u1.id < u2.id else (u2, u1)
                Friendship.objects.update_or_create(
                    user_a=a,
                    user_b=b,
                    defaults={
                        "initiated_by": u1,
                        "status": Friendship.Status.ACCEPTED,
                    },
                )

            make_friendship(users["demo_alex"], users["demo_jordan"])
            make_friendship(users["demo_alex"], users["demo_sam"])
            # Note: demo_taylor is NOT friends with demo_alex, enabling stranger privacy demonstration

            # 4. Active Event
            event, _ = GravityEvent.objects.update_or_create(
                slug="mulehacks-boost-2026",
                defaults={
                    "name": "MuleHacks 2026 Activity Boost",
                    "description": "Hackathon 2x XP Multiplier! Get moving between coding sessions.",
                    "icon": "⚡",
                    "is_active": True,
                    "starts_at": now - timedelta(hours=3),
                    "ends_at": now + timedelta(hours=36),
                    "xp_multiplier": 2.0,
                    "flat_xp_bonus": 25,
                },
            )
            self.stdout.write(f"Active Gravity Event: {event.name}")

            # 5. Active Season
            season, _ = Season.objects.update_or_create(
                slug="mulehacks-s1",
                defaults={
                    "name": "MuleHacks Season 1",
                    "description": "Inaugural Campus Athletic Season",
                    "is_enabled": True,
                    "starts_at": now - timedelta(days=7),
                    "ends_at": now + timedelta(days=30),
                },
            )
            # Add season standings for Basketball
            SeasonStanding.objects.update_or_create(
                season=season, user=users["demo_alex"], activity_type=basketball,
                defaults={"metric_name": "season_xp", "value": 1250.0, "rank": 1}
            )
            SeasonStanding.objects.update_or_create(
                season=season, user=users["demo_jordan"], activity_type=basketball,
                defaults={"metric_name": "season_xp", "value": 820.0, "rank": 2}
            )
            SeasonStanding.objects.update_or_create(
                season=season, user=users["demo_sam"], activity_type=basketball,
                defaults={"metric_name": "season_xp", "value": 540.0, "rank": 3}
            )

            # 6. Active Challenge
            metric_wins = ActivityMetric.objects.filter(activity_type=pickleball, slug="wins").first()
            if not metric_wins:
                metric_wins = ActivityMetric.objects.filter(activity_type=basketball, slug="points").first()

            challenge, _ = FriendChallenge.objects.update_or_create(
                title="[Demo] First to 5 Pickleball Wins",
                created_by=users["demo_alex"],
                defaults={
                    "activity_type": pickleball,
                    "metric": metric_wins,
                    "challenge_type": FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                    "target_value": 5.0,
                    "starts_at": now - timedelta(hours=12),
                    "ends_at": now + timedelta(days=3),
                    "status": FriendChallenge.Status.ACTIVE,
                },
            )
            ChallengeParticipant.objects.update_or_create(
                challenge=challenge,
                user=users["demo_alex"],
                defaults={
                    "invitation_status": ChallengeParticipant.InvitationStatus.ACCEPTED,
                    "joined_at": now - timedelta(hours=12),
                    "progress": 3.0,
                },
            )
            ChallengeParticipant.objects.update_or_create(
                challenge=challenge,
                user=users["demo_jordan"],
                defaults={
                    "invitation_status": ChallengeParticipant.InvitationStatus.ACCEPTED,
                    "joined_at": now - timedelta(hours=10),
                    "progress": 2.0,
                },
            )
            self.stdout.write(f"Active Friend Challenge: {challenge.title}")

            # 7. Live Sessions (Map & Pulse Now)
            live_specs = [
                {
                    "label": "[Demo] East Court Pickup Game",
                    "activity": basketball,
                    "creator": users["demo_jordan"],
                    "offset": (0.0018, -0.0012),
                    "participants": [users["demo_jordan"], users["demo_sam"]],
                    "started_ago_mins": 35,
                },
                {
                    "label": "[Demo] Library Group Study",
                    "activity": studying,
                    "creator": users["demo_taylor"],
                    "offset": (-0.0015, 0.0015),
                    "participants": [users["demo_taylor"]],
                    "started_ago_mins": 50,
                },
                {
                    "label": "[Demo] Campus Perimeter Jog",
                    "activity": running,
                    "creator": users["demo_alex"],
                    "offset": (0.0028, 0.0022),
                    "participants": [users["demo_alex"]],
                    "started_ago_mins": 20,
                },
                {
                    "label": "[Demo] Strength & Conditioning",
                    "activity": workout,
                    "creator": users["demo_sam"],
                    "offset": (-0.0022, -0.0025),
                    "participants": [],
                    "started_ago_mins": 15,
                },
            ]

            for s_spec in live_specs:
                s_lat = center_lat + s_spec["offset"][0]
                s_lng = center_lng + s_spec["offset"][1]
                sess_started = now - timedelta(minutes=s_spec["started_ago_mins"])
                sess, _ = ActivitySession.objects.update_or_create(
                    label=s_spec["label"],
                    defaults={
                        "activity_type": s_spec["activity"],
                        "created_by": s_spec["creator"],
                        "location": Point(s_lng, s_lat, srid=4326),
                        "status": ActivitySession.Status.ACTIVE,
                    },
                )
                ActivitySession.objects.filter(id=sess.id).update(started_at=sess_started)
                # Add active participants
                for p_user in s_spec["participants"]:
                    part, _ = Participation.objects.update_or_create(
                        session=sess,
                        user=p_user,
                        defaults={
                            "status": Participation.Status.ACTIVE,
                            "join_method": Participation.JoinMethod.SELF if p_user == s_spec["creator"] else Participation.JoinMethod.QR,
                        },
                    )
                    Participation.objects.filter(id=part.id).update(joined_at=sess_started)

            self.stdout.write(f"Seeded {len(live_specs)} live active sessions.")

            # 8. Historical Concluded Sessions (for Area History & Pulse Soon)
            # Area History: 14 sessions in past 28 days
            history_activities = [basketball, basketball, basketball, studying, studying, workout, running]
            for i, act in enumerate(history_activities):
                days_ago = (i * 3) + 2
                sess_time = now - timedelta(days=days_ago, hours=(i % 4) + 1)
                h_lat = center_lat + ((i % 3 - 1) * 0.0010)
                h_lng = center_lng + ((i % 2 - 0.5) * 0.0015)

                h_sess = ActivitySession.objects.create(
                    label=f"[Demo] Historical {act.name} Session #{i+1}",
                    activity_type=act,
                    created_by=users["demo_alex"],
                    location=Point(h_lng, h_lat, srid=4326),
                    status=ActivitySession.Status.ENDED,
                    ended_at=sess_time + timedelta(minutes=75),
                )
                ActivitySession.objects.filter(id=h_sess.id).update(started_at=sess_time)
                for u_name in ["demo_alex", "demo_jordan", "demo_sam"]:
                    p = Participation.objects.create(
                        session=h_sess,
                        user=users[u_name],
                        status=Participation.Status.COMPLETED,
                        join_method=Participation.JoinMethod.SELF,
                        left_at=sess_time + timedelta(minutes=75),
                    )
                    Participation.objects.filter(id=p.id).update(joined_at=sess_time)

            # Pulse Soon: Recurring Basketball sessions matching current diurnal 2-hour window & weekday across 4 past weeks
            local_now = timezone.localtime(now)
            curr_window_start_hour = (local_now.hour // 2) * 2
            forecast_cell_lat = center_lat + 0.0060 # ~650m away in distinct coarse cell
            forecast_cell_lng = center_lng + 0.0060

            for week_idx in range(1, 5): # 1, 2, 3, 4 weeks ago
                # Exactly same weekday and same diurnal start hour!
                past_session_dt = local_now - timedelta(weeks=week_idx)
                past_session_dt = past_session_dt.replace(
                    hour=curr_window_start_hour,
                    minute=15,
                    second=0,
                    microsecond=0
                )
                rec_sess = ActivitySession.objects.create(
                    label=f"[Demo] Recurring Basketball W-{week_idx}",
                    activity_type=basketball,
                    created_by=users["demo_alex"],
                    location=Point(forecast_cell_lng, forecast_cell_lat, srid=4326),
                    status=ActivitySession.Status.ENDED,
                    ended_at=past_session_dt + timedelta(minutes=80),
                )
                ActivitySession.objects.filter(id=rec_sess.id).update(started_at=past_session_dt)
                for u_name in ["demo_alex", "demo_jordan", "demo_sam", "demo_taylor"]:
                    p = Participation.objects.create(
                        session=rec_sess,
                        user=users[u_name],
                        status=Participation.Status.COMPLETED,
                        join_method=Participation.JoinMethod.SELF,
                        left_at=past_session_dt + timedelta(minutes=80),
                    )
                    Participation.objects.filter(id=p.id).update(joined_at=past_session_dt)

            self.stdout.write(f"Seeded recurring historical sessions for Pulse Soon (diurnal window: {curr_window_start_hour:02d}:00-{curr_window_start_hour+2:02d}:00).")

        self.stdout.write(self.style.SUCCESS("Demo dataset successfully initialized!"))
