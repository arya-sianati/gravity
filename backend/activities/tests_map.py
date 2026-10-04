from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import ActivityType, ActivitySession, Participation

User = get_user_model()

class LiveMapTest(TestCase):
    def setUp(self):
        self.user_exact = User.objects.create_user(username="uexact", password="pw", location_privacy_mode=User.PrivacyMode.EXACT)
        self.user_blur = User.objects.create_user(username="ublur", password="pw", location_privacy_mode=User.PrivacyMode.BLURRED)
        self.user_hide = User.objects.create_user(username="uhide", password="pw", location_privacy_mode=User.PrivacyMode.HIDDEN)
        
        self.activity = ActivityType.objects.create(name="MapTest", slug="maptest", is_active=True, heat_weight_multiplier=2.0)
        self.client = APIClient()

    def test_bbox_query(self):
        # 1. Valid bbox returns active session
        s1 = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_exact, location=Point(10, 10, srid=4326))
        Participation.objects.create(session=s1, user=self.user_exact, status=Participation.Status.ACTIVE)
        
        # 2. Session outside bbox omitted
        s2 = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_blur, location=Point(20, 20, srid=4326))
        Participation.objects.create(session=s2, user=self.user_blur, status=Participation.Status.ACTIVE)
        
        url = reverse('map-live')
        res = self.client.get(url, {'bbox': '9,9,11,11'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        features = res.data['features']
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]['properties']['session_id'], str(s1.id))
        
        # 4 & 5. Participant count and heat weight
        self.assertEqual(features[0]['properties']['participant_count'], 1)
        self.assertEqual(features[0]['properties']['weight'], 2.0)

    def test_ended_session_omitted(self):
        # 3. Ended session omitted
        s1 = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_exact, location=Point(10, 10, srid=4326), status=ActivitySession.Status.ENDED)
        Participation.objects.create(session=s1, user=self.user_exact, status=Participation.Status.LEFT)
        
        res = self.client.get(reverse('map-live'), {'bbox': '9,9,11,11'})
        self.assertEqual(len(res.data['features']), 0)

    def test_malformed_bbox_rejected(self):
        # 7. Malformed bbox
        res = self.client.get(reverse('map-live'), {'bbox': 'invalid'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
        res2 = self.client.get(reverse('map-live'), {'bbox': '10,10,0,0'}) # Invalid bounds
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_privacy_modes(self):
        s_exact = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_exact, location=Point(10.001, 10.001, srid=4326))
        Participation.objects.create(session=s_exact, user=self.user_exact, status=Participation.Status.ACTIVE)

        s_blur = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_blur, location=Point(10.001, 10.001, srid=4326))
        Participation.objects.create(session=s_blur, user=self.user_blur, status=Participation.Status.ACTIVE)

        s_hide = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_hide, location=Point(10.001, 10.001, srid=4326))
        Participation.objects.create(session=s_hide, user=self.user_hide, status=Participation.Status.ACTIVE)
        
        res = self.client.get(reverse('map-live'), {'bbox': '9,9,11,11'})
        features = res.data['features']
        
        self.assertEqual(len(features), 2) # Hidden is omitted completely
        
        # Exact check
        exact_feat = next(f for f in features if f['properties']['session_id'] == str(s_exact.id))
        self.assertEqual(exact_feat['geometry']['coordinates'], [10.001, 10.001])
        
        # Blurred check
        blur_feat = next(f for f in features if f['properties']['session_id'] == str(s_blur.id))
        self.assertNotEqual(blur_feat['geometry']['coordinates'], [10.001, 10.001])
        self.assertEqual(blur_feat['geometry']['coordinates'], [10.000, 10.000]) # snapped to nearest 0.005

    def test_session_detail_privacy_audit(self):
        # 13. session-detail endpoint does not bypass privacy (does not expose raw location)
        s_blur = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user_blur, location=Point(10.001, 10.001, srid=4326))
        self.client.force_authenticate(user=self.user_exact)
        res = self.client.get(reverse('session-detail', args=[s_blur.id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Assert location/lat/lng are NOT in the response body!
        self.assertNotIn('location', res.data)
        self.assertNotIn('lat', res.data)
        self.assertNotIn('lng', res.data)

