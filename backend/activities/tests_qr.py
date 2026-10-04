from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import ActivityType, ActivitySession, Participation

User = get_user_model()

class QRJoinTest(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator", password="pw")
        self.joiner = User.objects.create_user(username="joiner", password="pw")
        self.rando = User.objects.create_user(username="rando", password="pw")
        
        self.activity = ActivityType.objects.create(name="Basketball", slug="basketball", is_active=True, qr_join_enabled=True)
        self.session = ActivitySession.objects.create(
            activity_type=self.activity,
            created_by=self.creator,
            location=Point(10, 10, srid=4326),
            label="Pick Up Game"
        )
        Participation.objects.create(session=self.session, user=self.creator, status=Participation.Status.ACTIVE)
        
        self.creator_client = APIClient()
        self.creator_client.force_authenticate(user=self.creator)
        
        self.joiner_client = APIClient()
        self.joiner_client.force_authenticate(user=self.joiner)
        
        self.unauth_client = APIClient()

    def test_get_join_code_by_active_participant(self):
        # 1. active participant can request join code
        url = reverse('session-join-code', args=[self.session.id])
        res = self.creator_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('join_url', res.data)
        self.assertIn(str(self.session.join_token), res.data['join_url'])

    def test_get_join_code_by_non_participant(self):
        # 2. non-participant cannot request join code
        url = reverse('session-join-code', args=[self.session.id])
        
        rando_client = APIClient()
        rando_client.force_authenticate(user=self.rando)
        
        res = rando_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_preview_valid_token(self):
        # 4, 13, 14. valid preview succeeds, no location, no identities
        url = reverse('join-token', args=[self.session.join_token])
        res = self.unauth_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['activity']['name'], "Basketball")
        self.assertEqual(res.data['label'], "Pick Up Game")
        self.assertEqual(res.data['participant_count'], 1)
        
        # Security/Privacy assertions
        self.assertNotIn('location', res.data)
        self.assertNotIn('lat', res.data)
        self.assertNotIn('lng', res.data)
        self.assertNotIn('created_by', res.data)
        self.assertNotIn('username', res.data)

    def test_preview_invalid_token(self):
        # 5. invalid token rejected
        url = reverse('join-token', args=['00000000-0000-0000-0000-000000000000'])
        res = self.unauth_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_preview_ended_session(self):
        # 6. ended-session token rejected
        self.session.status = ActivitySession.Status.ENDED
        self.session.save()
        
        url = reverse('join-token', args=[self.session.join_token])
        res = self.unauth_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_unauthenticated(self):
        # 8. unauthenticated QR join rejected
        url = reverse('join-token', args=[self.session.join_token])
        res = self.unauth_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_join_authenticated(self):
        # 9, 10. authenticated QR join succeeds, join method recorded as QR
        url = reverse('join-token', args=[self.session.join_token])
        res = self.joiner_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        participation = Participation.objects.get(session=self.session, user=self.joiner)
        self.assertEqual(participation.status, Participation.Status.ACTIVE)
        self.assertEqual(participation.join_method, Participation.JoinMethod.QR)

    def test_join_duplicate(self):
        # 12. duplicate same-session join prevented
        Participation.objects.create(session=self.session, user=self.joiner, status=Participation.Status.ACTIVE)
        
        url = reverse('join-token', args=[self.session.join_token])
        res = self.joiner_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_join_conflict(self):
        # 11. existing active participation conflict preserved
        s2 = ActivitySession.objects.create(
            activity_type=self.activity,
            created_by=self.joiner,
            location=Point(20, 20, srid=4326)
        )
        Participation.objects.create(session=s2, user=self.joiner, status=Participation.Status.ACTIVE)
        
        url = reverse('join-token', args=[self.session.join_token])
        res = self.joiner_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

