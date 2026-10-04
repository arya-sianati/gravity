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
    GravityEvent,
)
from activities.logic.forecast_service import get_pulse_soon, snap_to_grid

User = get_user_model()


class PulseSoonForecastTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users (to meet min_participants threshold of 3)
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
            default_xp=25,
        )
        self.act_running = ActivityType.objects.create(
            name='Running',
            slug='running',
            icon='🏃',
            color='#33FF57',
            sort_order=2,
            default_xp=20,
        )

        # Base Coordinates (Warrensburg, MO: 38.7621, -93.7361)
        self.center_lat = 38.7621
        self.center_lng = -93.7361
        self.center_point = Point(self.center_lng, self.center_lat, srid=4326)

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

    def _seed_recurring_history(self, activity_type, location, target_weekday, target_hour, weeks_count, users, now):
        """
        Seeds historical sessions on a target weekday and hour for N distinct preceding weeks.
        """
        local_now = timezone.localtime(now)
        # Find the most recent date with target_weekday in the past
        days_back = (local_now.weekday() - target_weekday) % 7
        if days_back == 0:
            days_back = 7 # Start from previous week so historical sessions are in the past

        most_recent_day = local_now - timedelta(days=days_back)

        sessions = []
        for w in range(weeks_count):
            sess_dt = (most_recent_day - timedelta(weeks=w)).replace(
                hour=target_hour, minute=0, second=0, microsecond=0
            )
            sess = self._create_session(
                activity_type=activity_type,
                created_by=users[0],
                location=location,
                status=ActivitySession.Status.ENDED,
                started_at=sess_dt,
                ended_at=sess_dt + timedelta(hours=1, minutes=30),
            )
            for u in users:
                self._create_participation(
                    session=sess,
                    user=u,
                    status=Participation.Status.COMPLETED,
                    joined_at=sess_dt,
                    left_at=sess_dt + timedelta(hours=1, minutes=30),
                )
            sessions.append(sess)
        return sessions

    # -------------------------------------------------------------------------
    # 1. Recurring Pattern Produces Forecast
    # -------------------------------------------------------------------------
    def test_recurring_pattern_produces_forecast(self):
        """Historical activity meeting recurrence, unique users, and horizon criteria produces a forecast."""
        # Simulated 'now': Tuesday at 17:15 (target window is Tuesday 18:00 - 20:00)
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        # Force Tuesday (weekday 1)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Seed 4 weeks of Tuesday 18:00 Basketball history with 3 users
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1, # Tuesday
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            horizon_minutes=120,
            now=now,
        )

        self.assertEqual(len(res['items']), 1)
        item = res['items'][0]
        self.assertEqual(item['activity']['slug'], 'basketball')
        self.assertGreaterEqual(item['confidence_score'], 0.55)
        self.assertIn("18:00", item['expected_window']['starts_at'])
        self.assertIn("Tuesday", item['reason'])

    # -------------------------------------------------------------------------
    # 2. One-Off Activity Does NOT Produce Forecast
    # -------------------------------------------------------------------------
    def test_one_off_activity_does_not_produce_forecast(self):
        """An isolated one-time activity must not generate a forecast."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Only 1 occurrence 1 week ago
        self._seed_recurring_history(
            activity_type=self.act_running,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=1,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 3. Insufficient Distinct Weeks Suppressed
    # -------------------------------------------------------------------------
    def test_insufficient_distinct_weeks_suppressed(self):
        """Multiple sessions occurring within only 2 distinct weeks do NOT satisfy recurrence threshold."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # 2 distinct weeks (even if 4 total sessions)
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=2,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        # Must be empty because min_occurrences = 3
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 4. Insufficient Unique Users Suppressed (Solo Home Workout Anonymity)
    # -------------------------------------------------------------------------
    def test_insufficient_unique_users_suppressed(self):
        """Recurring activity with fewer than 3 unique participants is suppressed to protect privacy."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # 4 weeks of activity, but ONLY 1 user (Alice)
        self._seed_recurring_history(
            activity_type=self.act_running,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 5. Correct Weekday Pattern Matching
    # -------------------------------------------------------------------------
    def test_correct_weekday_pattern_matching(self):
        """Forecast for Tuesday activity does not surface when current day is Sunday."""
        # Current day is Sunday at 17:15
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_sunday = (6 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_sunday)

        # Seed Tuesday history
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1, # Tuesday
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        # Sunday does not match Tuesday recurring pattern
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 6. Correct Time Window Pattern Matching (Horizon Bounded)
    # -------------------------------------------------------------------------
    def test_correct_time_window_pattern_matching(self):
        """Evening 18:00 pattern is not forecasted during morning 10:00 (outside 2-hour horizon)."""
        # Tuesday at 10:00 AM
        local_now = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Tuesday 18:00 pattern
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            horizon_minutes=120, # 2 hours
            now=now,
        )
        # 18:00 is 8 hours away, outside 2-hour horizon
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 7. Outside Radius Excluded
    # -------------------------------------------------------------------------
    def test_outside_radius_excluded(self):
        """Distant recurring activity outside query radius is excluded."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Far location (~15km away: 0.14 deg lat)
        far_point = Point(self.center_lng, self.center_lat + 0.14, srid=4326)

        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=far_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000, # 2km radius
            now=now,
        )
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 8. Lookback Window Respected (Older Than 8 Weeks Excluded)
    # -------------------------------------------------------------------------
    def test_lookback_window_respected(self):
        """Sessions older than 8 weeks (56 days) do not count toward recurring threshold."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Create 4 sessions, but all from 10–14 weeks ago (70+ days ago)
        for w in range(10, 14):
            sess_dt = (now - timedelta(weeks=w)).replace(hour=18, minute=0, second=0, microsecond=0)
            sess = self._create_session(
                activity_type=self.act_bball,
                created_by=self.user1,
                location=self.center_point,
                status=ActivitySession.Status.ENDED,
                started_at=sess_dt,
                ended_at=sess_dt + timedelta(hours=1),
            )
            for u in [self.user1, self.user2, self.user3]:
                self._create_participation(
                    session=sess,
                    user=u,
                    status=Participation.Status.COMPLETED,
                    joined_at=sess_dt,
                    left_at=sess_dt + timedelta(hours=1),
                )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        # All sessions older than 56 days lookback -> 0 items
        self.assertEqual(len(res['items']), 0)

    # -------------------------------------------------------------------------
    # 9. Confidence Rises with Stronger Recurrence
    # -------------------------------------------------------------------------
    def test_confidence_rises_with_stronger_recurrence(self):
        """Pattern with 6 matching weeks has higher confidence score than 3 matching weeks."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Cell A: Basketball (6 matching weeks, 4 users)
        loc_a = self.center_point
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=loc_a,
            target_weekday=1,
            target_hour=18,
            weeks_count=6,
            users=[self.user1, self.user2, self.user3, self.user4],
            now=now,
        )

        # Cell B: Running (3 matching weeks, 3 users, at a slightly offset grid cell ~800m away)
        loc_b = Point(self.center_lng, self.center_lat + 0.008, srid=4326)
        self._seed_recurring_history(
            activity_type=self.act_running,
            location=loc_b,
            target_weekday=1,
            target_hour=18,
            weeks_count=3,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=3000,
            now=now,
        )

        self.assertEqual(len(res['items']), 2)
        bball_item = next(i for i in res['items'] if i['activity']['slug'] == 'basketball')
        running_item = next(i for i in res['items'] if i['activity']['slug'] == 'running')

        self.assertGreater(bball_item['confidence_score'], running_item['confidence_score'])

    # -------------------------------------------------------------------------
    # 10. Recency Weighting
    # -------------------------------------------------------------------------
    def test_recency_weighting(self):
        """Recent occurrences receive higher recency weight in confidence calculation."""
        from activities.logic.forecast_service import compute_forecast_confidence

        conf_recent = compute_forecast_confidence(
            distinct_weeks=4,
            eligible_weeks=8,
            avg_participants=5.0,
            days_since_latest=7.0, # 1 week ago
        )
        conf_older = compute_forecast_confidence(
            distinct_weeks=4,
            eligible_weeks=8,
            avg_participants=5.0,
            days_since_latest=40.0, # ~6 weeks ago
        )

        self.assertGreater(conf_recent, conf_older)

    # -------------------------------------------------------------------------
    # 11. Dynamic Pickleball Forecast Support
    # -------------------------------------------------------------------------
    def test_dynamic_pickleball_forecast(self):
        """Custom dynamically created ActivityType (Pickleball) forecasts seamlessly."""
        pickleball = ActivityType.objects.create(
            name='Pickleball',
            slug='pickleball-forecast-test',
            icon='🏓',
            color='#10B981',
            sort_order=7,
        )

        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        self._seed_recurring_history(
            activity_type=pickleball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )

        self.assertEqual(len(res['items']), 1)
        item = res['items'][0]
        self.assertEqual(item['activity']['name'], 'Pickleball')
        self.assertEqual(item['activity']['slug'], 'pickleball-forecast-test')
        self.assertEqual(item['activity']['icon'], '🏓')
        self.assertEqual(item['activity']['color'], '#10B981')

    # -------------------------------------------------------------------------
    # 12. No Raw Historical Coordinates or User Identities in Payload
    # -------------------------------------------------------------------------
    def test_no_raw_historical_coordinates_or_identities(self):
        """Payload never leaks raw session coordinates, user IDs, or usernames."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Specific point that is not on a round grid step
        precise_point = Point(-93.736184, 38.762193, srid=4326)

        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=precise_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )

        self.assertEqual(len(res['items']), 1)
        item = res['items'][0]

        # Ensure raw coordinates are not exposed
        self.assertNotEqual(item['area']['lat'], 38.762193)
        self.assertNotEqual(item['area']['lng'], -93.736184)

        # Top-level item must not leak user references
        self.assertNotIn('user_id', item)
        self.assertNotIn('user', item)
        self.assertNotIn('username', item)

    # -------------------------------------------------------------------------
    # 13. Forecast Uses Aggregate Geometry
    # -------------------------------------------------------------------------
    def test_forecast_uses_aggregate_geometry(self):
        """Forecast items supply GeoJSON Polygon geometry for hatched/patterned map overlay."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )

        item = res['items'][0]
        self.assertIn('geometry', item)
        self.assertEqual(item['geometry']['type'], 'Polygon')
        self.assertEqual(len(item['geometry']['coordinates']), 1)
        self.assertGreaterEqual(len(item['geometry']['coordinates'][0]), 16)

    # -------------------------------------------------------------------------
    # 14. Live Duplicate Suppression
    # -------------------------------------------------------------------------
    def test_live_duplicate_suppression(self):
        """Active live session for the same activity in the same cell suppresses redundant Soon prediction."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Seed recurring history
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        # Initially, Soon prediction is present
        res1 = get_pulse_soon(lat=self.center_lat, lng=self.center_lng, radius_m=2000, now=now)
        self.assertEqual(len(res1['items']), 1)

        # Create an ACTIVE Basketball session in the same grid cell
        live_sess = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user1,
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE,
        )
        Participation.objects.create(
            session=live_sess,
            user=self.user1,
            status=Participation.Status.ACTIVE,
        )

        # Query Soon again: prediction must be suppressed because it is already live!
        res2 = get_pulse_soon(lat=self.center_lat, lng=self.center_lng, radius_m=2000, now=now)
        self.assertEqual(len(res2['items']), 0)

    # -------------------------------------------------------------------------
    # 15. Activity Filter Query Parameter
    # -------------------------------------------------------------------------
    def test_activity_filter_query_parameter(self):
        """Filtering by activity slug returns only matching activity forecasts."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Basketball
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        # Running (different cell)
        loc_run = Point(self.center_lng, self.center_lat + 0.008, srid=4326)
        self._seed_recurring_history(
            activity_type=self.act_running,
            location=loc_run,
            target_weekday=1,
            target_hour=18,
            weeks_count=4,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res_bball = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=3000,
            activity_slug='basketball',
            now=now,
        )
        self.assertEqual(len(res_bball['items']), 1)
        self.assertEqual(res_bball['items'][0]['activity']['slug'], 'basketball')

    # -------------------------------------------------------------------------
    # 16. API Validation and Error Handling
    # -------------------------------------------------------------------------
    def test_api_validation_and_error_handling(self):
        """GET /api/pulse/soon/ handles required coordinates and parameter validation."""
        # 1. Missing lat/lng
        r1 = self.client.get('/api/pulse/soon/')
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Invalid coordinates
        r2 = self.client.get('/api/pulse/soon/?lat=invalid&lng=-93.7')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Invalid radius
        r3 = self.client.get('/api/pulse/soon/?lat=38.7&lng=-93.7&radius=-50')
        self.assertEqual(r3.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Invalid horizon
        r4 = self.client.get('/api/pulse/soon/?lat=38.7&lng=-93.7&horizon_minutes=0')
        self.assertEqual(r4.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Valid request
        r5 = self.client.get('/api/pulse/soon/?lat=38.7621&lng=-93.7361&radius=5000')
        self.assertEqual(r5.status_code, status.HTTP_200_OK)
        self.assertIn('items', r5.json())

    # -------------------------------------------------------------------------
    # 17. Deterministic Ordering
    # -------------------------------------------------------------------------
    def test_deterministic_ordering(self):
        """Forecasts sorted primarily by confidence desc, window start asc."""
        local_now = timezone.localtime().replace(hour=17, minute=15, second=0, microsecond=0)
        days_to_tuesday = (1 - local_now.weekday()) % 7
        now = local_now + timedelta(days=days_to_tuesday)

        # Pattern A: 5 weeks recurrence (higher confidence)
        self._seed_recurring_history(
            activity_type=self.act_bball,
            location=self.center_point,
            target_weekday=1,
            target_hour=18,
            weeks_count=5,
            users=[self.user1, self.user2, self.user3, self.user4],
            now=now,
        )

        # Pattern B: 3 weeks recurrence (lower confidence)
        loc_b = Point(self.center_lng, self.center_lat + 0.008, srid=4326)
        self._seed_recurring_history(
            activity_type=self.act_running,
            location=loc_b,
            target_weekday=1,
            target_hour=18,
            weeks_count=3,
            users=[self.user1, self.user2, self.user3],
            now=now,
        )

        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=3000,
            now=now,
        )
        self.assertEqual(len(res['items']), 2)
        # Higher confidence first
        self.assertGreaterEqual(res['items'][0]['confidence_score'], res['items'][1]['confidence_score'])
        self.assertEqual(res['items'][0]['activity']['slug'], 'basketball')

    # -------------------------------------------------------------------------
    # 18. Empty Sparse Data Response
    # -------------------------------------------------------------------------
    def test_empty_sparse_data_response(self):
        """Sparse area returns empty items list without raising errors."""
        now = timezone.now()
        res = get_pulse_soon(
            lat=self.center_lat,
            lng=self.center_lng,
            radius_m=2000,
            now=now,
        )
        self.assertEqual(res, {"items": []})
