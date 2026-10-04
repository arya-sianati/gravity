from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.management import call_command
from .models import Badge, UserBadge, Streak, ActivityType, ActivitySession, Participation
from .logic.badge_service import award_badge
from .logic.streak_service import evaluate_streak
from .logic.achievement_service import evaluate_after_participation
from datetime import timedelta
import io

User = get_user_model()

class BadgeAndStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pw')
        self.act1 = ActivityType.objects.create(name='A1', slug='a1')
        self.act2 = ActivityType.objects.create(name='A2', slug='a2')
        self.act3 = ActivityType.objects.create(name='A3', slug='a3')
        
        call_command('seed_badges', stdout=io.StringIO())

    def create_participation(self, act_type, days_ago=0):
        from django.contrib.gis.geos import Point
        session = ActivitySession.objects.create(activity_type=act_type, created_by=self.user, location=Point(0,0))
        part = Participation.objects.create(session=session, user=self.user, status=Participation.Status.COMPLETED)
        part.left_at = timezone.now() - timedelta(days=days_ago)
        part.save()
        return part

    def test_badge_awarded_once(self):
        ub1, c1 = award_badge(self.user, 'first-pull')
        self.assertTrue(c1)
        self.assertEqual(UserBadge.objects.count(), 1)
        
        ub2, c2 = award_badge(self.user, 'first-pull')
        self.assertFalse(c2)
        self.assertEqual(UserBadge.objects.count(), 1)

    def test_streak_evaluation(self):
        # Day 1
        p1 = self.create_participation(self.act1, days_ago=2)
        s, inc, new_longest = evaluate_streak(self.user, p1)
        self.assertEqual(s.current_count, 1)
        self.assertTrue(inc)
        
        # Day 1 again
        p2 = self.create_participation(self.act1, days_ago=2)
        s, inc, new_longest = evaluate_streak(self.user, p2)
        self.assertEqual(s.current_count, 1)
        self.assertFalse(inc)

        # Day 2
        p3 = self.create_participation(self.act1, days_ago=1)
        s, inc, new_longest = evaluate_streak(self.user, p3)
        self.assertEqual(s.current_count, 2)
        self.assertEqual(s.longest_count, 2)

        # Skip a day, go to today (days_ago=0) -> this means 1 day missed relative to 'days_ago=1'
        # Wait, if yesterday was days_ago=1, and today is days_ago=0, that is consecutive!
        # Let's do it right.
        p4 = self.create_participation(self.act1, days_ago=0)
        s, inc, new_longest = evaluate_streak(self.user, p4)
        self.assertEqual(s.current_count, 3)
        
        # Reset user streak and simulate missed day
        s.delete()
        p_old = self.create_participation(self.act1, days_ago=5)
        evaluate_streak(self.user, p_old)
        
        p_now = self.create_participation(self.act1, days_ago=0)
        s, inc, new_longest = evaluate_streak(self.user, p_now)
        # Re-started streak
        self.assertEqual(s.current_count, 1)
        # Longest remains 1 here since it was fresh
        self.assertEqual(s.longest_count, 1)

    def test_achievements_evaluation(self):
        # 1 activity -> First pull
        p1 = self.create_participation(self.act1)
        earned = evaluate_after_participation(self.user, p1, None)
        self.assertEqual(len(earned), 1)
        self.assertEqual(earned[0].slug, 'first-pull')
        
        # Next 3 activities (total 4) -> Nothing
        for _ in range(3):
            self.create_participation(self.act1)
            
        # 5th activity -> Getting Started
        p5 = self.create_participation(self.act1)
        earned = evaluate_after_participation(self.user, p5, None)
        self.assertEqual(len(earned), 1)
        self.assertEqual(earned[0].slug, 'getting-started')

        # Explorer
        self.create_participation(self.act2)
        p7 = self.create_participation(self.act3)
        earned = evaluate_after_participation(self.user, p7, None)
        self.assertEqual(len(earned), 1)
        self.assertEqual(earned[0].slug, 'explorer')

    def test_leave_endpoint_integration(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        
        from django.contrib.gis.geos import Point
        session = ActivitySession.objects.create(activity_type=self.act1, created_by=self.user, location=Point(1,1))
        # Ensure it has been long enough for XP
        p = Participation.objects.create(
            session=session, user=self.user, 
            status=Participation.Status.ACTIVE
        )
        Participation.objects.filter(id=p.id).update(joined_at=timezone.now() - timedelta(minutes=5))
        p.refresh_from_db()
        
        res = client.post(f'/api/sessions/{session.id}/leave/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn('xp_awarded', data)
        self.assertIn('streak', data)
        self.assertIn('badges_earned', data)
        
        # It's their first pull
        self.assertEqual(len(data['badges_earned']), 1)
        self.assertEqual(data['badges_earned'][0]['slug'], 'first-pull')
        
        # Streak should be 1
        self.assertEqual(data['streak']['current'], 1)
