from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from .models import ActivityType, ActivityMetric, ActivitySession, Participation, MetricValue
from datetime import timedelta

User = get_user_model()

class MetricsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pw')
        self.user2 = User.objects.create_user(username='testuser2', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.act_run = ActivityType.objects.create(name='Running', slug='running')
        self.metric_dist = ActivityMetric.objects.create(
            activity_type=self.act_run, name='Distance', slug='distance',
            data_type=ActivityMetric.DataType.DECIMAL, unit='mi',
            is_primary=True, min_value=0.0
        )
        
        self.act_bb = ActivityType.objects.create(name='Basketball', slug='basketball')
        self.metric_pts = ActivityMetric.objects.create(
            activity_type=self.act_bb, name='Points', slug='points',
            data_type=ActivityMetric.DataType.INTEGER,
            is_primary=True, min_value=0.0
        )
        self.metric_dur = ActivityMetric.objects.create(
            activity_type=self.act_bb, name='Duration', slug='duration',
            data_type=ActivityMetric.DataType.DURATION, unit='minutes'
        )
        
        self.session = ActivitySession.objects.create(activity_type=self.act_bb, created_by=self.user, location=Point(10, 10))
        self.participation = Participation.objects.create(session=self.session, user=self.user, status=Participation.Status.ACTIVE)

    def test_valid_integer_metric(self):
        res = self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'points': 15})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(MetricValue.objects.get().value, 15.0)

    def test_non_integer_rejected(self):
        res = self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'points': 15.5})
        self.assertEqual(res.status_code, 400)
        self.assertIn('points', res.json())

    def test_negative_rejected(self):
        res = self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'points': -5})
        self.assertEqual(res.status_code, 400)
        
    def test_wrong_activity_rejected(self):
        res = self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'distance': 5.0})
        self.assertEqual(res.status_code, 400)

    def test_update_replaces(self):
        self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'points': 10})
        self.client.patch(f'/api/participations/{self.participation.id}/metrics/', {'points': 20})
        self.assertEqual(MetricValue.objects.count(), 1)
        self.assertEqual(MetricValue.objects.get().value, 20.0)

    def test_auto_duration_on_leave(self):
        # We manually set joined_at to 10 mins ago
        self.participation.joined_at = timezone.now() - timedelta(minutes=10)
        self.participation.save()
        
        res = self.client.post(f'/api/sessions/{self.session.id}/leave/')
        self.assertEqual(res.status_code, 200)
        
        self.participation.refresh_from_db()
        self.assertEqual(self.participation.status, Participation.Status.LEFT)
        dur = MetricValue.objects.get(metric=self.metric_dur)
        # Should be approx 10 minutes
        self.assertTrue(9.5 <= dur.value <= 10.5)

    def test_leaderboard(self):
        self.participation.status = Participation.Status.COMPLETED
        self.participation.save()
        MetricValue.objects.create(participation=self.participation, metric=self.metric_pts, value=10)
        
        # User2 participation
        p2 = Participation.objects.create(session=self.session, user=self.user2, status=Participation.Status.COMPLETED)
        MetricValue.objects.create(participation=p2, metric=self.metric_pts, value=25)
        
        res = self.client.get('/api/leaderboards/basketball/?period=all')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data['rows']), 2)
        self.assertEqual(data['rows'][0]['user']['display_name'], 'testuser2')
        self.assertEqual(data['rows'][0]['rank'], 1)
        self.assertEqual(data['rows'][1]['user']['display_name'], 'testuser')
        self.assertEqual(data['rows'][1]['rank'], 2)

    def test_dynamic_pickleball_leaderboard(self):
        act_pb = ActivityType.objects.create(name='Pickleball', slug='pickleball')
        metric_wins = ActivityMetric.objects.create(
            activity_type=act_pb, name='Games Won', slug='games-won',
            data_type=ActivityMetric.DataType.INTEGER, unit='wins',
            is_primary=True, min_value=0.0, aggregation=ActivityMetric.AggregationMode.SUM
        )
        
        session_pb = ActivitySession.objects.create(activity_type=act_pb, created_by=self.user, location=Point(20, 20))
        p1 = Participation.objects.create(session=session_pb, user=self.user, status=Participation.Status.COMPLETED)
        p2 = Participation.objects.create(session=session_pb, user=self.user2, status=Participation.Status.COMPLETED)
        
        MetricValue.objects.create(participation=p1, metric=metric_wins, value=3)
        MetricValue.objects.create(participation=p2, metric=metric_wins, value=5)
        
        # Second session to check sum
        session_pb2 = ActivitySession.objects.create(activity_type=act_pb, created_by=self.user, location=Point(20, 20))
        p1_2 = Participation.objects.create(session=session_pb2, user=self.user, status=Participation.Status.COMPLETED)
        MetricValue.objects.create(participation=p1_2, metric=metric_wins, value=4)
        
        res = self.client.get('/api/leaderboards/pickleball/?period=all')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['metric']['slug'], 'games-won')
        self.assertEqual(data['metric']['unit'], 'wins')
        self.assertEqual(len(data['rows']), 2)
        
        # User 1 has 3 + 4 = 7 wins
        # User 2 has 5 wins
        self.assertEqual(data['rows'][0]['user']['display_name'], 'testuser')
        self.assertEqual(data['rows'][0]['value'], 7.0)
        self.assertEqual(data['rows'][0]['rank'], 1)
        
        self.assertEqual(data['rows'][1]['user']['display_name'], 'testuser2')
        self.assertEqual(data['rows'][1]['value'], 5.0)
        self.assertEqual(data['rows'][1]['rank'], 2)

    def test_competition_ranking_ties(self):
        # We need 3 users
        u3 = User.objects.create_user(username='u3', password='pw')
        p1 = Participation.objects.create(session=self.session, user=self.user, status=Participation.Status.COMPLETED)
        p2 = Participation.objects.create(session=self.session, user=self.user2, status=Participation.Status.COMPLETED)
        p3 = Participation.objects.create(session=self.session, user=u3, status=Participation.Status.COMPLETED)
        
        MetricValue.objects.create(participation=p1, metric=self.metric_pts, value=100)
        MetricValue.objects.create(participation=p2, metric=self.metric_pts, value=100)
        MetricValue.objects.create(participation=p3, metric=self.metric_pts, value=90)
        
        res = self.client.get('/api/leaderboards/basketball/?period=all')
        rows = res.json()['rows']
        
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['value'], 100.0)
        self.assertEqual(rows[0]['rank'], 1)
        
        self.assertEqual(rows[1]['value'], 100.0)
        self.assertEqual(rows[1]['rank'], 1)
        
        self.assertEqual(rows[2]['value'], 90.0)
        self.assertEqual(rows[2]['rank'], 3) # Competition ranking: 1, 1, 3
