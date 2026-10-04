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
