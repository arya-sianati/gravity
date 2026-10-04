from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import ActivityType, ActivitySession, Participation

User = get_user_model()

class Phase06AcceptanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pw")
        self.user2 = User.objects.create_user(username="u2", password="pw")
        self.activity = ActivityType.objects.create(name="Basketball", slug="basketball", is_active=True, join_suggestion_radius_m=100)
        self.disabled_activity = ActivityType.objects.create(name="Old", slug="old", is_active=False)
        self.other_activity = ActivityType.objects.create(name="Other", slug="other", is_active=True)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.unauth_client = APIClient()

    def test_unauth_rejected(self):
        # 2 & 20: Unauthenticated session creation & mutations rejected
        url = reverse('session-list')
        res = self.unauth_client.post(url, {'activity_type': self.activity.id, 'lat': 10, 'lng': 10})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test join unauth
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user, location=Point(10, 10, srid=4326))
        res2 = self.unauth_client.post(reverse('session-join', args=[session.id]))
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)

    def test_disabled_activity_rejected(self):
        # 3: Starting a disabled Activity Type is rejected
        url = reverse('session-list')
        res = self.client.post(url, {'activity_type': self.disabled_activity.id, 'lat': 10, 'lng': 10})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_lat_lng_rejected(self):
        # 4: Invalid latitude/longitude is rejected
        url = reverse('session-list')
        res = self.client.post(url, {'activity_type': self.activity.id, 'lat': 'invalid', 'lng': 10})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_label_stored(self):
        # 6: Other can store its custom label
        url = reverse('session-list')
        res = self.client.post(url, {'activity_type': self.other_activity.id, 'lat': 10, 'lng': 10, 'label': 'Pickleball'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        session = ActivitySession.objects.get(id=res.data['id'])
        self.assertEqual(session.label, 'Pickleball')

    def test_cannot_join_ended_session(self):
        # 11: Ended/cancelled sessions cannot be joined
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user2, location=Point(10, 10, srid=4326), status=ActivitySession.Status.ENDED)
        res = self.client.post(reverse('session-join', args=[session.id]))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_leaving_does_not_end_session_if_others_present(self):
        # 13: Creator leaving does NOT end the session while another active participant remains
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user, location=Point(10, 10, srid=4326))
        Participation.objects.create(session=session, user=self.user, status=Participation.Status.ACTIVE)
        Participation.objects.create(session=session, user=self.user2, status=Participation.Status.ACTIVE)
        
        url = reverse('session-leave', args=[session.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        session.refresh_from_db()
        self.assertEqual(session.status, ActivitySession.Status.ACTIVE) # Session still active
        
        # Now user2 leaves
        client2 = APIClient()
        client2.force_authenticate(user=self.user2)
        res2 = client2.post(reverse('session-leave', args=[session.id]))
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        
        session.refresh_from_db()
        self.assertEqual(session.status, ActivitySession.Status.ENDED) # Session ended
        
    def test_nearby_different_activity_omitted(self):
        # 18: Different Activity Type is omitted
        session = ActivitySession.objects.create(activity_type=self.other_activity, created_by=self.user2, location=Point(-73.0, 40.0, srid=4326))
        Participation.objects.create(session=session, user=self.user2, status=Participation.Status.ACTIVE)
        
        url = reverse('session-nearby')
        res = self.client.get(url, {'activity': 'basketball', 'lat': 40.0, 'lng': -73.0})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0) # Should be 0 since the nearby session is 'other'

