from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from activities.models import ActivityType, ActivityMetric

class ActivityTypeModelTest(TestCase):
    def test_create_activity_type(self):
        activity = ActivityType.objects.create(
            name="Tennis",
            slug="tennis",
            icon="🎾",
            color="#00FF00"
        )
        self.assertEqual(activity.name, "Tennis")
        self.assertEqual(activity.slug, "tennis")
        self.assertTrue(activity.is_active)

    def test_duplicate_slug_raises_error(self):
        ActivityType.objects.create(name="Tennis", slug="tennis")
        with self.assertRaises(IntegrityError):
            ActivityType.objects.create(name="Another Tennis", slug="tennis")

class ActivityMetricModelTest(TestCase):
    def setUp(self):
        self.activity = ActivityType.objects.create(name="Tennis", slug="tennis")

    def test_create_activity_metric(self):
        metric = ActivityMetric.objects.create(
            activity_type=self.activity,
            name="Sets Won",
            slug="sets-won",
            is_primary=True
        )
        self.assertEqual(metric.name, "Sets Won")
        self.assertEqual(metric.activity_type, self.activity)

    def test_duplicate_metric_slug_per_activity_raises_error(self):
        ActivityMetric.objects.create(activity_type=self.activity, name="Metric 1", slug="m1")
        with self.assertRaises(IntegrityError):
            ActivityMetric.objects.create(activity_type=self.activity, name="Metric 2", slug="m1")

    def test_duplicate_primary_metric_per_activity_raises_error(self):
        ActivityMetric.objects.create(activity_type=self.activity, name="M1", slug="m1", is_primary=True)
        with self.assertRaises(IntegrityError):
            ActivityMetric.objects.create(activity_type=self.activity, name="M2", slug="m2", is_primary=True)

    def test_clean_validates_min_max_value(self):
        metric = ActivityMetric(
            activity_type=self.activity,
            name="M1",
            slug="m1",
            min_value=10,
            max_value=5
        )
        with self.assertRaises(ValidationError):
            metric.clean()

class ActivityTypeAPIViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active_activity = ActivityType.objects.create(name="Active", slug="active", is_active=True)
        ActivityMetric.objects.create(activity_type=self.active_activity, name="Score", slug="score", is_primary=True)
        self.inactive_activity = ActivityType.objects.create(name="Inactive", slug="inactive", is_active=False)

    def test_list_activity_types_excludes_inactive(self):
        url = reverse('activity-type-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['slug'], 'active')
        self.assertEqual(len(response.data[0]['metrics']), 1)

    def test_retrieve_active_activity_type(self):
        url = reverse('activity-type-detail', kwargs={'slug': 'active'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'active')

    def test_retrieve_inactive_activity_type_returns_404(self):
        url = reverse('activity-type-detail', kwargs={'slug': 'inactive'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

from django.core.management import call_command
from io import StringIO

class SeedGravityCommandTest(TestCase):
    def test_seed_idempotency_and_preservation(self):
        # Run seed for the first time
        out = StringIO()
        call_command('seed_gravity', stdout=out)
        self.assertIn("Successfully seeded activities!", out.getvalue())
        
        # Verify initial state
        running = ActivityType.objects.get(slug="running")
        self.assertEqual(running.name, "Running")
        self.assertTrue(running.gps_tracking_enabled)
        initial_count = ActivityType.objects.count()
        
        # Modify the activity (simulate admin edit)
        running.name = "Jogging"
        running.gps_tracking_enabled = False
        running.save()
        
        # Modify a metric
        distance = ActivityMetric.objects.get(activity_type=running, slug="distance")
        distance.name = "Miles"
        distance.save()

        # Run seed a second time
        out = StringIO()
        call_command('seed_gravity', stdout=out)
        self.assertIn("Preserved Activity", out.getvalue())
        
        # Verify no duplication occurred
        self.assertEqual(ActivityType.objects.count(), initial_count)
        
        # Verify the admin modifications were preserved
        running.refresh_from_db()
        self.assertEqual(running.name, "Jogging")
        self.assertFalse(running.gps_tracking_enabled)
        
        distance.refresh_from_db()
        self.assertEqual(distance.name, "Miles")

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import ActivitySession, Participation

User = get_user_model()

class ActivitySessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.user2 = User.objects.create_user(username="testuser2", password="password")
        self.activity = ActivityType.objects.create(name="Tennis", slug="tennis", is_active=True, join_suggestion_radius_m=100)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_session(self):
        url = reverse('session-list')
        data = {
            'activity_type': self.activity.id,
            'lat': 40.0,
            'lng': -73.0,
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ActivitySession.objects.count(), 1)
        self.assertEqual(Participation.objects.count(), 1)
        
        participation = Participation.objects.first()
        self.assertEqual(participation.user, self.user)
        self.assertEqual(participation.status, Participation.Status.ACTIVE)

    def test_duplicate_active_participation_fails(self):
        # Create first session
        session1 = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user, location=Point(-73.0, 40.0, srid=4326))
        Participation.objects.create(session=session1, user=self.user, status=Participation.Status.ACTIVE)
        
        # Try to create second session
        url = reverse('session-list')
        res = self.client.post(url, {'activity_type': self.activity.id, 'lat': 40.1, 'lng': -73.1})
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        
    def test_join_session(self):
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user2, location=Point(-73.0, 40.0, srid=4326))
        Participation.objects.create(session=session, user=self.user2, status=Participation.Status.ACTIVE)
        
        url = reverse('session-join', args=[session.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Participation.objects.filter(session=session).count(), 2)

    def test_leave_session(self):
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user, location=Point(-73.0, 40.0, srid=4326))
        part = Participation.objects.create(session=session, user=self.user, status=Participation.Status.ACTIVE)
        
        url = reverse('session-leave', args=[session.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.LEFT)
        self.assertIsNotNone(part.left_at)
        
        session.refresh_from_db()
        self.assertEqual(session.status, ActivitySession.Status.ENDED)
        self.assertIsNotNone(session.ended_at)

    def test_nearby_suggestion(self):
        session = ActivitySession.objects.create(activity_type=self.activity, created_by=self.user2, location=Point(-73.0, 40.0, srid=4326))
        Participation.objects.create(session=session, user=self.user2, status=Participation.Status.ACTIVE)
        
        url = reverse('session-nearby')
        res = self.client.get(url, {'activity': 'tennis', 'lat': 40.0001, 'lng': -73.0})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(session.id))
        
        # Test out of bounds
        res2 = self.client.get(url, {'activity': 'tennis', 'lat': 41.0, 'lng': -73.0})
        self.assertEqual(len(res2.data), 0)

