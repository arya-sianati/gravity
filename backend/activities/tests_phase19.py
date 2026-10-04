from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from activities.models import (
    ActivityType,
    ActivitySession,
    Participation,
    Season,
    GravityEvent,
)
from activities.logic.history_service import get_area_history

User = get_user_model()


class GravityHistoryTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.user1 = User.objects.create_user(username='alice', password='password123')
        self.user2 = User.objects.create_user(username='bob', password='password123')
        self.user3 = User.objects.create_user(username='charlie', password='password123')
        self.user4 = User.objects.create_user(username='david', password='password123')
        self.user5 = User.objects.create_user(username='emma', password='password123')

        # Base Activity Types
        self.act_bball = ActivityType.objects.create(
            name='Basketball',
            slug='basketball',
            icon='🏀',
            color='#FF5733',
            sort_order=1,
            default_xp=25
        )
        self.act_running = ActivityType.objects.create(
            name='Running',
            slug='running',
            icon='🏃',
            color='#33FF57',
            sort_order=2,
            default_xp=20
        )

        # Base Coordinates (e.g. Warrensburg, MO: 38.7621, -93.7361)
        self.center_lat = 38.7621
        self.center_lng = -93.7361
        self.center_point = Point(self.center_lng, self.center_lat, srid=4326)

        # Point ~200m away (inside 500m radius)
        # 0.0018 deg lat is ~200m
        self.inside_point = Point(self.center_lng, self.center_lat + 0.0018, srid=4326)

        # Point ~2500m away (outside 500m radius)
        # 0.025 deg lat is ~2700m
        self.outside_point = Point(self.center_lng, self.center_lat + 0.025, srid=4326)

    def _create_session(self, activity_type, created_by, location, status, started_at=None, ended_at=None):
        sess = ActivitySession.objects.create(
            activity_type=activity_type,
            created_by=created_by,
            location=location,
            status=status,
        )
        updates = {}
        if started_at is not None:
            updates['started_at'] = started_at
        if ended_at is not None:
            updates['ended_at'] = ended_at
        if updates:
            ActivitySession.objects.filter(id=sess.id).update(**updates)
            sess.refresh_from_db()
        return sess

    def _create_participation(self, session, user, status, joined_at=None, left_at=None):
        part = Participation.objects.create(
            session=session,
            user=user,
            status=status,
        )
        updates = {}
        if joined_at is not None:
            updates['joined_at'] = joined_at
        if left_at is not None:
            updates['left_at'] = left_at
        if updates:
            Participation.objects.filter(id=part.id).update(**updates)
            part.refresh_from_db()
        return part

    # -------------------------------------------------------------------------
    # 1. Spatial Bounds
    # -------------------------------------------------------------------------
    def test_spatial_bounds_filtering(self):
        """Sessions inside radius contribute; sessions outside radius are excluded."""
        now = timezone.now()

        # Inside session (3 participants)
        sess_in = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.inside_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess_in,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        # Outside session (3 participants)
        sess_out = self._create_session(
            activity_type=self.act_running,
            created_by=self.user4,
            location=self.outside_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user3, self.user4, self.user5]:
            self._create_participation(
                session=sess_out,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=500.0,
            period='30d',
            now=now
        )

        self.assertFalse(res['privacy_suppressed'])
        self.assertEqual(res['total_sessions'], 1)
        self.assertEqual(res['total_participations'], 3)
        self.assertEqual(res['total_unique_participants'], 3)
        self.assertEqual(len(res['activities']), 1)
        self.assertEqual(res['activities'][0]['slug'], 'basketball')

    # -------------------------------------------------------------------------
    # 2. Period Filtering
    # -------------------------------------------------------------------------
    def test_period_filtering(self):
        """Tests today, 7d, 30d, 90d, and all period filters."""
        now = timezone.now()

        def create_hist_session(days_ago, users, act):
            t_start = now - timedelta(days=days_ago, hours=2)
            t_end = now - timedelta(days=days_ago, hours=1)
            sess = self._create_session(
                activity_type=act,
                created_by=users[0],
                location=self.center_point,
                status=ActivitySession.Status.ENDED,
                started_at=t_start,
                ended_at=t_end,
            )
            for u in users:
                self._create_participation(
                    session=sess,
                    user=u,
                    status=Participation.Status.COMPLETED,
                    joined_at=t_start,
                    left_at=t_end,
                )
            return sess

        # 1. 2 hours ago (Today)
        create_hist_session(0, [self.user1, self.user2, self.user3], self.act_bball)

        # 2. 4 days ago (Within 7d)
        create_hist_session(4, [self.user1, self.user2, self.user4], self.act_running)

        # 3. 20 days ago (Within 30d)
        create_hist_session(20, [self.user1, self.user3, self.user5], self.act_bball)

        # 4. 60 days ago (Within 90d)
        create_hist_session(60, [self.user2, self.user3, self.user4], self.act_running)

        # 5. 150 days ago (Within all)
        create_hist_session(150, [self.user1, self.user4, self.user5], self.act_bball)

        # Test today
        r_today = get_area_history(self.center_lat, self.center_lng, period='today', now=now)
        self.assertEqual(r_today['total_sessions'], 1)
        self.assertEqual(r_today['total_participations'], 3)

        # Test 7d
        r_7d = get_area_history(self.center_lat, self.center_lng, period='7d', now=now)
        self.assertEqual(r_7d['total_sessions'], 2)
        self.assertEqual(r_7d['total_participations'], 6)

        # Test 30d
        r_30d = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertEqual(r_30d['total_sessions'], 3)
        self.assertEqual(r_30d['total_participations'], 9)

        # Test 90d
        r_90d = get_area_history(self.center_lat, self.center_lng, period='90d', now=now)
        self.assertEqual(r_90d['total_sessions'], 4)
        self.assertEqual(r_90d['total_participations'], 12)

        # Test all
        r_all = get_area_history(self.center_lat, self.center_lng, period='all', now=now)
        self.assertEqual(r_all['total_sessions'], 5)
        self.assertEqual(r_all['total_participations'], 15)

    # -------------------------------------------------------------------------
    # 3. Season Period Filtering
    # -------------------------------------------------------------------------
    def test_season_period_filtering(self):
        """Active Season defines boundary for season period query."""
        now = timezone.now()
        season = Season.objects.create(
            name='Fall 2026',
            slug='fall-2026',
            starts_at=now - timedelta(days=15),
            ends_at=now + timedelta(days=15),
            is_enabled=True,
        )

        def make_sess(dt, users):
            sess = self._create_session(
                activity_type=self.act_bball,
                created_by=users[0],
                location=self.center_point,
                status=ActivitySession.Status.ENDED,
                started_at=dt,
                ended_at=dt + timedelta(hours=1),
            )
            for u in users:
                self._create_participation(
                    session=sess,
                    user=u,
                    status=Participation.Status.COMPLETED,
                    joined_at=dt,
                    left_at=dt + timedelta(hours=1),
                )
            return sess

        # Inside season (5 days ago)
        make_sess(now - timedelta(days=5), [self.user1, self.user2, self.user3])

        # Before season (25 days ago)
        make_sess(now - timedelta(days=25), [self.user1, self.user2, self.user4])

        res = get_area_history(self.center_lat, self.center_lng, period='season', now=now)
        self.assertEqual(res['total_sessions'], 1)
        self.assertEqual(res['total_participations'], 3)

    # -------------------------------------------------------------------------
    # 4. Qualifying Participation and Cancellation Filtering
    # -------------------------------------------------------------------------
    def test_cancelled_and_short_participations_excluded(self):
        """Cancelled sessions and participations under 60 seconds are excluded."""
        now = timezone.now()

        # 1. Cancelled session is excluded
        cancelled_sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.CANCELLED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=cancelled_sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        # 2. Valid session with 2 qualifying participations and 1 short participation (30s)
        valid_sess = self._create_session(
            activity_type=self.act_running,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        # Alice: 60 mins -> Qualifies
        self._create_participation(
            session=valid_sess,
            user=self.user1,
            status=Participation.Status.COMPLETED,
            joined_at=now - timedelta(hours=2),
            left_at=now - timedelta(hours=1),
        )
        # Bob: 30 mins -> Qualifies
        self._create_participation(
            session=valid_sess,
            user=self.user2,
            status=Participation.Status.LEFT,
            joined_at=now - timedelta(hours=2),
            left_at=now - timedelta(minutes=90),
        )
        # Charlie: 30 seconds -> Does NOT qualify (< 60s)
        self._create_participation(
            session=valid_sess,
            user=self.user3,
            status=Participation.Status.LEFT,
            joined_at=now - timedelta(hours=2),
            left_at=now - timedelta(hours=2) + timedelta(seconds=30),
        )

        # Because only Alice and Bob qualify, unique participants = 2 (< 3 threshold)
        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        # Should be suppressed due to small number
        self.assertTrue(res['privacy_suppressed'])
        self.assertEqual(res['total_sessions'], 0)

        # Now add David with 10 mins duration to valid_sess
        self._create_participation(
            session=valid_sess,
            user=self.user4,
            status=Participation.Status.AUTO_STOPPED,
            joined_at=now - timedelta(hours=2),
            left_at=now - timedelta(minutes=110),
        )

        res2 = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertFalse(res2['privacy_suppressed'])
        self.assertEqual(res2['total_sessions'], 1)
        self.assertEqual(res2['total_participations'], 3) # Alice, Bob, David (Charlie excluded)
        self.assertEqual(res2['total_unique_participants'], 3)

    # -------------------------------------------------------------------------
    # 5. Dominant Activity and Tie-Breaking
    # -------------------------------------------------------------------------
    def test_dominant_activity_determination_and_tie_breaker(self):
        """Dominant activity is chosen by participation volume, then session count."""
        now = timezone.now()

        # Session 1: Basketball (3 participants)
        s1 = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=3),
            ended_at=now - timedelta(hours=2),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=s1,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=3),
                left_at=now - timedelta(hours=2),
            )

        # Session 2: Running (2 participants)
        s2 = self._create_session(
            activity_type=self.act_running,
            created_by=self.user4,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user4, self.user5]:
            self._create_participation(
                session=s2,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertFalse(res['privacy_suppressed'])
        self.assertIsNotNone(res['dominant_activity'])
        self.assertEqual(res['dominant_activity']['slug'], 'basketball')
        self.assertEqual(res['dominant_activity']['participation_count'], 3)
        self.assertEqual(res['dominant_activity']['share_percentage'], 60.0)

        # Tie-breaker test: Add another Running session with 1 participant so Running reaches 3 participants
        # Running: 2 sessions, 3 participations
        # Basketball: 1 session, 3 participations
        # Running should win tie-breaker because session_count is higher!
        s3 = self._create_session(
            activity_type=self.act_running,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(minutes=45),
            ended_at=now - timedelta(minutes=15),
        )
        self._create_participation(
            session=s3,
            user=self.user1,
            status=Participation.Status.COMPLETED,
            joined_at=now - timedelta(minutes=45),
            left_at=now - timedelta(minutes=15),
        )

        res_tie = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertEqual(res_tie['dominant_activity']['slug'], 'running')
        self.assertEqual(res_tie['dominant_activity']['participation_count'], 3)
        self.assertEqual(res_tie['dominant_activity']['session_count'], 2)

    # -------------------------------------------------------------------------
    # 6. Events and XP Multipliers Do NOT Inflate History Volume
    # -------------------------------------------------------------------------
    def test_events_do_not_inflate_participation_volume(self):
        """XP multipliers / Event associations do NOT artificially multiply participation volume."""
        now = timezone.now()
        event = GravityEvent.objects.create(
            name='Double XP Night',
            slug='double-xp-night',
            activity_type=self.act_bball,
            xp_multiplier=2.5,
            flat_xp_bonus=50,
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
            is_active=True,
        )

        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertEqual(res['total_participations'], 3) # Strictly 3, not multiplied by 2.5
        self.assertEqual(res['dominant_activity']['participation_count'], 3)

    # -------------------------------------------------------------------------
    # 7. Time of Day 3-Hour Buckets and Peak Time
    # -------------------------------------------------------------------------
    def test_time_distribution_and_peak_time(self):
        """Identifies 3-hour bucket distribution and peak time."""
        now = timezone.now()
        # Choose a fixed afternoon time: 19:30 local time (Bucket 18:00 - 21:00)
        local_target = timezone.localtime(now).replace(hour=19, minute=30, second=0, microsecond=0)

        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=local_target,
            ended_at=local_target + timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=local_target,
                left_at=local_target + timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='all', now=now)
        self.assertEqual(res['peak_time'], '18:00 - 21:00')
        bucket_18_21 = next(b for b in res['time_distribution'] if b['label'] == '18:00 - 21:00')
        self.assertEqual(bucket_18_21['participation_count'], 3)
        self.assertEqual(bucket_18_21['session_count'], 1)

    # -------------------------------------------------------------------------
    # 8. Weekday Distribution and Busiest Day
    # -------------------------------------------------------------------------
    def test_weekday_distribution_and_busiest_day(self):
        """Correctly aggregates weekdays and identifies busiest day."""
        now = timezone.now()
        # Find the most recent Saturday
        local_now = timezone.localtime(now)
        days_since_saturday = (local_now.weekday() - 5) % 7
        if days_since_saturday == 0 and local_now.hour < 2:
            days_since_saturday = 7
        target_saturday = local_now - timedelta(days=days_since_saturday)
        sat_start = target_saturday.replace(hour=14, minute=0, second=0, microsecond=0)

        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=sat_start,
            ended_at=sat_start + timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=sat_start,
                left_at=sat_start + timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertEqual(res['busiest_day'], 'Saturday')
        sat_data = next(d for d in res['weekday_distribution'] if d['day'] == 'Saturday')
        self.assertEqual(sat_data['participation_count'], 3)

    # -------------------------------------------------------------------------
    # 9. Dynamic Activity Support (e.g. Pickleball)
    # -------------------------------------------------------------------------
    def test_dynamic_activity_type_support(self):
        """Newly created dynamic activity types work automatically."""
        pickleball = ActivityType.objects.create(
            name='Pickleball',
            slug='pickleball-history-test',
            icon='🏓',
            color='#10B981',
            sort_order=5,
        )
        now = timezone.now()

        sess = self._create_session(
            activity_type=pickleball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertIsNotNone(res['dominant_activity'])
        self.assertEqual(res['dominant_activity']['name'], 'Pickleball')
        self.assertEqual(res['dominant_activity']['slug'], 'pickleball-history-test')
        self.assertEqual(res['dominant_activity']['icon'], '🏓')
        self.assertEqual(res['dominant_activity']['color'], '#10B981')

    # -------------------------------------------------------------------------
    # 10. Privacy & Small-Number Suppression
    # -------------------------------------------------------------------------
    def test_privacy_small_number_suppression(self):
        """Areas with < 3 unique participants suppress details to prevent deanonymization."""
        now = timezone.now()

        # Only 2 participants (Alice and Bob)
        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertTrue(res['privacy_suppressed'])
        self.assertEqual(res['min_participants_required'], 3)
        self.assertEqual(res['total_sessions'], 0)
        self.assertEqual(res['total_participations'], 0)
        self.assertEqual(res['total_unique_participants'], 0)
        self.assertIsNone(res['dominant_activity'])
        self.assertEqual(res['activities'], [])
        self.assertEqual(res['time_distribution'], [])
        self.assertEqual(res['weekday_distribution'], [])

    # -------------------------------------------------------------------------
    # 11. Zero Activity Case
    # -------------------------------------------------------------------------
    def test_zero_activity_case(self):
        """Zero activity returns non-suppressed empty response with clear message."""
        now = timezone.now()
        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)
        self.assertFalse(res['privacy_suppressed'])
        self.assertEqual(res['total_sessions'], 0)
        self.assertEqual(res['total_participations'], 0)
        self.assertIsNone(res['dominant_activity'])
        self.assertEqual(res['activities'], [])
        self.assertIn("No activity history found", res['message'])

    # -------------------------------------------------------------------------
    # 12. Privacy Guarantee: No Raw User Coordinates or User IDs in Output
    # -------------------------------------------------------------------------
    def test_output_contains_no_user_ids_or_coordinates(self):
        """Ensures that user IDs, usernames, and raw location coordinates are absent."""
        now = timezone.now()

        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        res = get_area_history(self.center_lat, self.center_lng, period='30d', now=now)

        # Top-level should have no user data
        self.assertNotIn('user_id', res)
        self.assertNotIn('user', res)
        self.assertNotIn('username', res)

        for act in res['activities']:
            self.assertNotIn('user_id', act)
            self.assertNotIn('username', act)
            self.assertNotIn('coordinates', act)
            self.assertNotIn('lat', act)
            self.assertNotIn('lng', act)

    # -------------------------------------------------------------------------
    # 13. API View Endpoint: GET /api/history/area/
    # -------------------------------------------------------------------------
    def test_api_area_history_endpoint(self):
        """Tests GET /api/history/area/ with validation and response serialization."""
        now = timezone.now()

        sess = self._create_session(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        # 1. Missing lat/lng
        r1 = self.client.get('/api/history/area/')
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Invalid radius
        r2 = self.client.get(f'/api/history/area/?lat={self.center_lat}&lng={self.center_lng}&radius=-10')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Invalid period
        r3 = self.client.get(f'/api/history/area/?lat={self.center_lat}&lng={self.center_lng}&period=invalid')
        self.assertEqual(r3.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Valid query
        r4 = self.client.get(f'/api/history/area/?lat={self.center_lat}&lng={self.center_lng}&radius=500&period=30d')
        self.assertEqual(r4.status_code, status.HTTP_200_OK)
        data = r4.json()
        self.assertFalse(data['privacy_suppressed'])
        self.assertEqual(data['total_sessions'], 1)
        self.assertEqual(data['total_participations'], 3)
        self.assertEqual(data['dominant_activity']['slug'], 'basketball')

    # -------------------------------------------------------------------------
    # 14. API Alias Endpoint: GET /api/map/history/
    # -------------------------------------------------------------------------
    def test_api_map_history_alias_endpoint(self):
        """Tests that GET /api/map/history/ routes correctly to the same view."""
        now = timezone.now()

        sess = self._create_session(
            activity_type=self.act_running,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ENDED,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )
        for u in [self.user1, self.user2, self.user3]:
            self._create_participation(
                session=sess,
                user=u,
                status=Participation.Status.COMPLETED,
                joined_at=now - timedelta(hours=2),
                left_at=now - timedelta(hours=1),
            )

        r = self.client.get(f'/api/map/history/?lat={self.center_lat}&lng={self.center_lng}&radius=1000&period=7d')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertFalse(data['privacy_suppressed'])
        self.assertEqual(data['total_sessions'], 1)
        self.assertEqual(data['dominant_activity']['slug'], 'running')
