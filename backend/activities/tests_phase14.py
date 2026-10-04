from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import Season, SeasonStanding, SeasonRewardRule, SeasonRewardAward, ActivityType, ActivitySession, Participation, XPTransaction, Badge
from .logic.season_service import finalize_season, get_current_season
from datetime import timedelta

User = get_user_model()

class SeasonTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='tester1', password='pw')
        self.user2 = User.objects.create_user(username='tester2', password='pw')
        self.user3 = User.objects.create_user(username='tester3', password='pw')
        
        self.act = ActivityType.objects.create(name='Pickleball', slug='pickleball', default_xp=50)
        from .models import ActivityMetric
        self.metric = ActivityMetric.objects.create(
            activity_type=self.act,
            name='Games Won',
            slug='games-won',
            data_type=ActivityMetric.DataType.INTEGER,
            is_primary=True,
            leaderboard_enabled=True,
            aggregation=ActivityMetric.AggregationMode.SUM
        )
        
        self.badge = Badge.objects.create(name='Champ', slug='champ', is_active=True)
        
        self.now = timezone.now()
        
        self.season = Season.objects.create(
            name="Fall 2026",
            slug="fall-2026",
            starts_at=self.now - timedelta(days=30),
            ends_at=self.now - timedelta(days=1), # Already ended
            is_enabled=True
        )
        
        self.rule1 = SeasonRewardRule.objects.create(
            season=self.season,
            activity_type=self.act,
            min_rank=1,
            max_rank=1,
            xp_bonus=500,
            badge=self.badge
        )
        
        self.rule2 = SeasonRewardRule.objects.create(
            season=self.season,
            activity_type=self.act,
            min_rank=2,
            max_rank=3,
            xp_bonus=200
        )

    def create_participation(self, user, joined_at, metric_val):
        session = ActivitySession.objects.create(activity_type=self.act, created_by=user, location=Point(0,0))
        p = Participation.objects.create(session=session, user=user, status=Participation.Status.COMPLETED)
        Participation.objects.filter(id=p.id).update(joined_at=joined_at)
        p.refresh_from_db()
        from .models import MetricValue
        MetricValue.objects.create(participation=p, metric=self.metric, value=metric_val)
        return p

    def test_season_leaderboard_and_finalization(self):
        # In-season
        self.create_participation(self.user1, self.now - timedelta(days=10), 10) # 10 games
        self.create_participation(self.user2, self.now - timedelta(days=12), 8) # 8 games
        self.create_participation(self.user3, self.now - timedelta(days=15), 10) # 10 games (Tie for rank 1)
        
        # Out-of-season
        self.create_participation(self.user2, self.now, 20) # Too late
        self.create_participation(self.user1, self.now - timedelta(days=40), 20) # Too early
        
        # Test get_current_season
        self.assertIsNone(get_current_season()) # Season ended
        
        # Finalize
        res = finalize_season(self.season.slug)
        self.assertEqual(res['status'], 'success')
        
        # Standings
        st1 = SeasonStanding.objects.get(season=self.season, user=self.user1)
        st2 = SeasonStanding.objects.get(season=self.season, user=self.user2)
        st3 = SeasonStanding.objects.get(season=self.season, user=self.user3)
        
        self.assertEqual(st1.rank, 1)
        self.assertEqual(st3.rank, 1) # Competition tie
        self.assertEqual(st2.rank, 3) # Skip 2 due to tie
        
        # Rewards User 1
        aw1 = SeasonRewardAward.objects.get(season=self.season, user=self.user1)
        self.assertEqual(aw1.xp_awarded, 500)
        self.assertTrue(aw1.badge_awarded)
        xpt1 = XPTransaction.objects.filter(user=self.user1, reason=XPTransaction.Reason.SEASON).first()
        self.assertEqual(xpt1.amount, 500)
        
        # Rewards User 3
        aw3 = SeasonRewardAward.objects.get(season=self.season, user=self.user3)
        self.assertEqual(aw3.xp_awarded, 500)
        
        # Rewards User 2
        aw2 = SeasonRewardAward.objects.get(season=self.season, user=self.user2)
        self.assertEqual(aw2.xp_awarded, 200) # Rank 3
        self.assertFalse(aw2.badge_awarded)

    def test_season_overlap_rejection(self):
        from django.core.exceptions import ValidationError
        Season.objects.all().delete()
        
        s1 = Season(
            name="Fall", slug="fall",
            starts_at=self.now, ends_at=self.now + timedelta(days=30), is_enabled=True
        )
        s1.clean()
        s1.save()
        
        s2 = Season(
            name="Winter", slug="winter",
            starts_at=self.now + timedelta(days=10), ends_at=self.now + timedelta(days=40), is_enabled=True
        )
        with self.assertRaises(ValidationError):
            s2.clean()
