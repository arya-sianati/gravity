from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from .models import ActivityType, ActivitySession, Participation, XPTransaction
from .logic.xp_service import award_xp, level_for_xp, xp_for_level
from datetime import timedelta
from django.conf import settings

User = get_user_model()

class XPTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pw')
        self.user2 = User.objects.create_user(username='testuser2', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.act = ActivityType.objects.create(name='Basketball', slug='basketball', default_xp=100)
        self.session = ActivitySession.objects.create(activity_type=self.act, created_by=self.user, location=Point(10, 10))
        self.participation = Participation.objects.create(session=self.session, user=self.user, status=Participation.Status.ACTIVE)

    def test_level_curve(self):
        self.assertEqual(level_for_xp(0), 1)
        self.assertEqual(level_for_xp(100), 2)
        self.assertEqual(level_for_xp(250), 3)
        self.assertEqual(level_for_xp(450), 4)
        
        self.assertEqual(xp_for_level(1), 0)
        self.assertEqual(xp_for_level(2), 100)
        self.assertEqual(xp_for_level(3), 250)
        self.assertEqual(xp_for_level(4), 450)

    def test_award_xp_updates_user(self):
        award_xp(self.user, 100, 'participation')
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 100)
        self.assertEqual(self.user.current_level, 2)
        
        award_xp(self.user, 150, 'streak')
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 250)
        self.assertEqual(self.user.current_level, 3)

    def test_negative_xp_boundaries(self):
        award_xp(self.user, 50, 'participation')
        award_xp(self.user, -100, 'adjustment')
        self.user.refresh_from_db()
        # Should clamp to 0 and level 1
        self.assertEqual(self.user.total_xp, 0)
        self.assertEqual(self.user.current_level, 1)

    def test_participation_idempotency(self):
        x1 = award_xp(self.user, 50, 'participation', participation=self.participation)
        self.assertIsNotNone(x1)
        
        x2 = award_xp(self.user, 50, 'participation', participation=self.participation)
        self.assertIsNone(x2) # Repeated participation xp fails gracefully
        
        self.assertEqual(XPTransaction.objects.count(), 1)

    def test_leave_grants_xp_if_qualified(self):
        # Move joined_at backward 2 minutes
        self.participation.joined_at = timezone.now() - timedelta(minutes=2)
        self.participation.save()
        
        res = self.client.post(f'/api/sessions/{self.session.id}/leave/')
        self.assertEqual(res.status_code, 200)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 100) # Default XP of basketball
        
        # Test idempotency via direct service call since leave doesn't call it again
        self.assertEqual(XPTransaction.objects.count(), 1)
        
    def test_leave_does_not_grant_xp_if_short(self):
        self.participation.joined_at = timezone.now() - timedelta(seconds=10) # 10 secs
        self.participation.save()
        
        res = self.client.post(f'/api/sessions/{self.session.id}/leave/')
        self.assertEqual(res.status_code, 200)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 0)

    def test_xp_history_endpoint(self):
        award_xp(self.user, 100, 'participation')
        res = self.client.get('/api/me/xp-history/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]['amount'], 100)

