from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.test import APIClient
from rest_framework import status

from activities.models import (
    ActivityType,
    ActivityMetric,
    ActivitySession,
    Participation,
    MetricValue,
    FriendChallenge,
    ChallengeParticipant,
    XPTransaction,
)
from activities.logic.autostop_service import (
    finalize_participation,
    process_location_heartbeat,
)
from activities.logic.challenge_service import create_challenge, accept_challenge_invitation
from accounts.models import Friendship

User = get_user_model()


class AutoStopSessionIntegrityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_alice = User.objects.create_user(username='alice', password='password123')
        self.user_bob = User.objects.create_user(username='bob', password='password123')
        self.user_charlie = User.objects.create_user(username='charlie', password='password123')

        # Base Anchor Location: (lng, lat) = (-93.7361, 38.7621)
        self.anchor_point = Point(-93.7361, 38.7621, srid=4326)

        # 1. Basketball: anchor_radius mode, radius=100m, grace=30s
        self.act_bball = ActivityType.objects.create(
            name='Basketball',
            slug='basketball-test',
            icon='🏀',
            color='#F59E0B',
            auto_stop_enabled=True,
            auto_stop_mode=ActivityType.AutoStopMode.ANCHOR_RADIUS,
            auto_stop_radius_m=100.0,
            auto_stop_grace_seconds=30,
            default_xp=25
        )
        self.bball_duration = ActivityMetric.objects.create(
            activity_type=self.act_bball,
            name='Duration',
            slug='duration',
            unit='min',
            data_type=ActivityMetric.DataType.DURATION,
            aggregation=ActivityMetric.AggregationMode.SUM
        )

        # 2. Running: movement activity, auto_stop disabled
        self.act_running = ActivityType.objects.create(
            name='Running',
            slug='running-test',
            icon='🏃',
            color='#3B82F6',
            auto_stop_enabled=False,
            auto_stop_mode=ActivityType.AutoStopMode.DISABLED,
            gps_tracking_enabled=True,
            default_xp=30
        )
        self.run_duration = ActivityMetric.objects.create(
            activity_type=self.act_running,
            name='Duration',
            slug='duration',
            unit='min',
            data_type=ActivityMetric.DataType.DURATION,
            aggregation=ActivityMetric.AggregationMode.SUM
        )

        # 3. Studying: zero grace test activity
        self.act_zero_grace = ActivityType.objects.create(
            name='Studying Zero Grace',
            slug='studying-zero-test',
            icon='📚',
            color='#10B981',
            auto_stop_enabled=True,
            auto_stop_mode=ActivityType.AutoStopMode.ANCHOR_RADIUS,
            auto_stop_radius_m=50.0,
            auto_stop_grace_seconds=0,
            default_xp=15
        )

    # -------------------------------------------------------------------------
    # 1. Inside radius remains active
    # -------------------------------------------------------------------------
    def test_inside_radius_remains_active(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        # Heartbeat at exact anchor location
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7621,
            lng=-93.7361
        )
        self.assertEqual(res['participation_status'], 'active')
        self.assertTrue(res['inside_activity_area'])
        self.assertIsNone(res['outside_since'])
        self.assertFalse(res['auto_stopped'])

        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.ACTIVE)
        self.assertIsNone(part.outside_since)
        self.assertIsNotNone(part.last_heartbeat_at)

    # -------------------------------------------------------------------------
    # 2. First outside heartbeat starts grace
    # -------------------------------------------------------------------------
    def test_first_outside_heartbeat_starts_grace(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        # Heartbeat ~500m north (clearly outside 100m radius)
        now_t0 = timezone.now()
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7665,
            lng=-93.7361,
            now=now_t0
        )
        self.assertEqual(res['participation_status'], 'active')
        self.assertFalse(res['inside_activity_area'])
        self.assertIsNotNone(res['outside_since'])
        self.assertEqual(res['grace_remaining_seconds'], 30)
        self.assertFalse(res['auto_stopped'])

        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.ACTIVE)
        self.assertIsNotNone(part.outside_since)

    # -------------------------------------------------------------------------
    # 3. Continued outside beyond grace auto-stops
    # -------------------------------------------------------------------------
    def test_continued_outside_beyond_grace_autostops(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        t0 = timezone.now() - timedelta(minutes=5)
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE,
            joined_at=t0
        )

        # 1st outside heartbeat: sets outside_since
        process_location_heartbeat(
            user=self.user_alice,
            lat=38.7665,
            lng=-93.7361,
            now=t0 + timedelta(seconds=60)
        )

        # 2nd outside heartbeat 35s later (> 30s grace)
        t_after_grace = t0 + timedelta(seconds=95)
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7665,
            lng=-93.7361,
            now=t_after_grace
        )

        self.assertEqual(res['participation_status'], 'auto_stopped')
        self.assertTrue(res['auto_stopped'])
        self.assertEqual(res['grace_remaining_seconds'], 0)
        self.assertIn("left the activity area", res['completion']['detail'])

        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.AUTO_STOPPED)
        self.assertEqual(part.left_at, t_after_grace)
        session.refresh_from_db()
        self.assertEqual(session.status, ActivitySession.Status.ENDED)

    # -------------------------------------------------------------------------
    # 4. Returning inside clears grace
    # -------------------------------------------------------------------------
    def test_returning_inside_clears_grace(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        t0 = timezone.now()
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE,
            joined_at=t0
        )

        # 1. Step outside: grace begins
        res1 = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7665,
            lng=-93.7361,
            now=t0 + timedelta(seconds=5)
        )
        self.assertFalse(res1['inside_activity_area'])
        self.assertIsNotNone(res1['outside_since'])

        # 2. Step back inside within grace period (15s < 30s)
        res2 = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7621,
            lng=-93.7361,
            now=t0 + timedelta(seconds=20)
        )
        self.assertTrue(res2['inside_activity_area'])
        self.assertIsNone(res2['outside_since'])
        self.assertFalse(res2['auto_stopped'])

        part.refresh_from_db()
        self.assertIsNone(part.outside_since)
        self.assertEqual(part.status, Participation.Status.ACTIVE)

        # 3. Later step outside again: starts fresh 30s grace
        res3 = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7665,
            lng=-93.7361,
            now=t0 + timedelta(seconds=40)
        )
        self.assertFalse(res3['inside_activity_area'])
        self.assertEqual(res3['grace_remaining_seconds'], 30)

    # -------------------------------------------------------------------------
    # 5. Exact radius counts as inside
    # -------------------------------------------------------------------------
    def test_exact_radius_counts_as_inside(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        test_pt = Point(-93.7361, 38.7625, srid=4326)
        computed_dist = ActivitySession.objects.filter(id=session.id).annotate(
            d=Distance('location', test_pt)
        ).first().d.m

        # Set radius to exactly match computed distance
        self.act_bball.auto_stop_radius_m = computed_dist
        self.act_bball.save(update_fields=['auto_stop_radius_m'])

        # Requirement 29: Distance <= radius is inside
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7625,
            lng=-93.7361
        )
        self.assertTrue(res['inside_activity_area'])
        self.assertEqual(res['participation_status'], 'active')

    # -------------------------------------------------------------------------
    # 6. Zero grace auto-stops immediately
    # -------------------------------------------------------------------------
    def test_zero_grace_autostops_immediately(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_zero_grace,
            created_by=self.user_bob,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_bob,
            status=Participation.Status.ACTIVE
        )

        # First heartbeat outside with grace=0 must auto-stop immediately
        res = process_location_heartbeat(
            user=self.user_bob,
            lat=38.7700,
            lng=-93.7361
        )
        self.assertTrue(res['auto_stopped'])
        self.assertEqual(res['participation_status'], 'auto_stopped')

        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.AUTO_STOPPED)

    # -------------------------------------------------------------------------
    # 7. Disabled auto-stop never radius-stops
    # -------------------------------------------------------------------------
    def test_disabled_autostop_never_stops(self):
        # Configure activity with auto_stop_enabled=False
        act_disabled = ActivityType.objects.create(
            name='No AutoStop',
            slug='no-autostop-test',
            icon='🚫',
            color='#999999',
            auto_stop_enabled=False,
            auto_stop_mode=ActivityType.AutoStopMode.DISABLED,
            auto_stop_radius_m=10.0,
            auto_stop_grace_seconds=0
        )
        session = ActivitySession.objects.create(
            activity_type=act_disabled,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        # Heartbeat 10 kilometers away
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.8500,
            lng=-93.7361
        )
        self.assertFalse(res['auto_stopped'])
        self.assertEqual(res['participation_status'], 'active')
        self.assertTrue(res['inside_activity_area'])

    # -------------------------------------------------------------------------
    # 8. Running/default movement activity does not use anchor-radius
    # -------------------------------------------------------------------------
    def test_running_movement_activity_does_not_use_anchor_radius(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        # Runner moves 5 km away from starting point
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.8000,
            lng=-93.7361
        )
        self.assertEqual(res['participation_status'], 'active')
        self.assertTrue(res['inside_activity_area'])
        self.assertFalse(res['auto_stopped'])
        self.assertIsNone(res['outside_since'])

        part.refresh_from_db()
        self.assertEqual(part.status, Participation.Status.ACTIVE)

    # -------------------------------------------------------------------------
    # 9. Invalid coordinates rejected
    # -------------------------------------------------------------------------
    def test_invalid_coordinates_rejected(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        self.client.force_authenticate(user=self.user_alice)

        # Latitude > 90
        res1 = self.client.post('/api/me/activity-location/', {'lat': 120.0, 'lng': -93.0}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # Longitude < -180
        res2 = self.client.post('/api/me/activity-location/', {'lat': 38.0, 'lng': -200.0}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

        # Non-numeric
        res3 = self.client.post('/api/me/activity-location/', {'lat': 'invalid', 'lng': 'coord'}, format='json')
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 10. Unauthenticated heartbeat rejected
    # -------------------------------------------------------------------------
    def test_unauthenticated_heartbeat_rejected(self):
        self.client.logout()
        res = self.client.post('/api/me/activity-location/', {'lat': 38.7621, 'lng': -93.7361}, format='json')
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # -------------------------------------------------------------------------
    # 11. Heartbeat cannot operate on another user's Participation
    # -------------------------------------------------------------------------
    def test_heartbeat_cannot_operate_on_another_users_participation(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        part_alice = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        # Bob attempts to submit heartbeat targeting Alice's participation ID
        self.client.force_authenticate(user=self.user_bob)
        res = self.client.post(
            f'/api/participations/{part_alice.id}/heartbeat/',
            {'lat': 38.7621, 'lng': -93.7361},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 12. Auto-stop one participant while others remain keeps Session active
    # -------------------------------------------------------------------------
    def test_autostop_one_participant_keeps_session_active(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        t0 = timezone.now() - timedelta(minutes=5)
        part_alice = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE,
            joined_at=t0
        )
        part_bob = Participation.objects.create(
            session=session,
            user=self.user_bob,
            status=Participation.Status.ACTIVE,
            joined_at=t0
        )

        # Alice moves away and auto-stops
        process_location_heartbeat(
            user=self.user_alice,
            lat=38.7700,
            lng=-93.7361,
            now=t0
        )
        res = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7700,
            lng=-93.7361,
            now=t0 + timedelta(seconds=40)
        )
        self.assertTrue(res['auto_stopped'])

        part_alice.refresh_from_db()
        part_bob.refresh_from_db()
        session.refresh_from_db()

        self.assertEqual(part_alice.status, Participation.Status.AUTO_STOPPED)
        self.assertEqual(part_bob.status, Participation.Status.ACTIVE)
        # Session remains ACTIVE because Bob is still participating
        self.assertEqual(session.status, ActivitySession.Status.ACTIVE)

    # -------------------------------------------------------------------------
    # 13. Final participant auto-stop ends Session
    # -------------------------------------------------------------------------
    def test_final_participant_autostop_ends_session(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        t0 = timezone.now() - timedelta(minutes=5)
        part_alice = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE,
            joined_at=t0
        )

        # Alice is the only participant; auto-stopping terminates session
        process_location_heartbeat(user=self.user_alice, lat=38.7700, lng=-93.7361, now=t0)
        process_location_heartbeat(user=self.user_alice, lat=38.7700, lng=-93.7361, now=t0 + timedelta(seconds=40))

        part_alice.refresh_from_db()
        session.refresh_from_db()

        self.assertEqual(part_alice.status, Participation.Status.AUTO_STOPPED)
        self.assertEqual(session.status, ActivitySession.Status.ENDED)
        self.assertIsNotNone(session.ended_at)

    # -------------------------------------------------------------------------
    # 14. Manual leave vs auto-stop race does not duplicate completion/rewards
    # -------------------------------------------------------------------------
    def test_manual_leave_vs_autostop_race_no_duplicate_rewards(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        t0 = timezone.now() - timedelta(minutes=5)
        part_alice = Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )
        Participation.objects.filter(id=part_alice.id).update(joined_at=t0)
        part_alice.refresh_from_db()

        # 1. User performs manual leave
        res1 = finalize_participation(
            participation_id=part_alice.id,
            left_status=Participation.Status.LEFT,
            left_time=timezone.now(),
            user=self.user_alice
        )
        self.assertEqual(res1['participation_status'], Participation.Status.LEFT)
        self.assertEqual(res1['xp_awarded'], 25)

        xp_count1 = XPTransaction.objects.filter(participation=part_alice).count()
        self.assertEqual(xp_count1, 1)

        # 2. Race: A competing heartbeat arrives after manual leave
        res2 = process_location_heartbeat(
            user=self.user_alice,
            lat=38.7700,
            lng=-93.7361,
            participation_id=part_alice.id
        )
        # Must detect that participation is already concluded
        self.assertTrue(res2.get('already_concluded'))
        self.assertFalse(res2.get('auto_stopped'))

        # Assert XP was NOT awarded twice
        xp_count2 = XPTransaction.objects.filter(participation=part_alice).count()
        self.assertEqual(xp_count2, 1)

    # -------------------------------------------------------------------------
    # 15. Dynamic Pickleball configuration works
    # -------------------------------------------------------------------------
    def test_dynamic_pickleball_acceptance(self):
        pickleball = ActivityType.objects.create(
            name='Pickleball',
            slug='pickleball-autostop-test',
            icon='🏓',
            color='#10B981',
            auto_stop_enabled=True,
            auto_stop_mode=ActivityType.AutoStopMode.ANCHOR_RADIUS,
            auto_stop_radius_m=100.0,
            auto_stop_grace_seconds=30,
            default_xp=20
        )
        session = ActivitySession.objects.create(
            activity_type=pickleball,
            created_by=self.user_charlie,
            location=self.anchor_point
        )
        part = Participation.objects.create(
            session=session,
            user=self.user_charlie,
            status=Participation.Status.ACTIVE
        )

        # 1. Inside anchor stays active
        res_in = process_location_heartbeat(
            user=self.user_charlie,
            lat=38.7621,
            lng=-93.7361
        )
        self.assertTrue(res_in['inside_activity_area'])
        self.assertEqual(res_in['participation_status'], 'active')

        # 2. Outside begins grace
        t0 = timezone.now()
        res_out = process_location_heartbeat(
            user=self.user_charlie,
            lat=38.7700,
            lng=-93.7361,
            now=t0
        )
        self.assertFalse(res_out['inside_activity_area'])
        self.assertEqual(res_out['grace_remaining_seconds'], 30)

        # 3. Beyond grace auto-stops
        res_stop = process_location_heartbeat(
            user=self.user_charlie,
            lat=38.7700,
            lng=-93.7361,
            now=t0 + timedelta(seconds=35)
        )
        self.assertTrue(res_stop['auto_stopped'])
        self.assertEqual(res_stop['participation_status'], 'auto_stopped')

    # -------------------------------------------------------------------------
    # 16. Heartbeat response exposes no raw location
    # -------------------------------------------------------------------------
    def test_heartbeat_response_exposes_no_raw_location(self):
        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        self.client.force_authenticate(user=self.user_alice)
        res = self.client.post('/api/me/activity-location/', {'lat': 38.7621, 'lng': -93.7361}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.json()
        self.assertNotIn('lat', data)
        self.assertNotIn('lng', data)
        self.assertNotIn('coordinates', data)
        self.assertNotIn('location', data)

    # -------------------------------------------------------------------------
    # 17. Raw heartbeat coordinates absent from WebSocket messages/log payloads
    # -------------------------------------------------------------------------
    def test_raw_heartbeat_coordinates_absent_from_websocket_payloads(self):
        from activities.signals import broadcast_session_update
        from unittest.mock import patch

        session = ActivitySession.objects.create(
            activity_type=self.act_bball,
            created_by=self.user_alice,
            location=self.anchor_point
        )
        Participation.objects.create(
            session=session,
            user=self.user_alice,
            status=Participation.Status.ACTIVE
        )

        with patch('activities.signals.async_to_sync') as mock_async_to_sync:
            mock_send = mock_async_to_sync.return_value
            broadcast_session_update(session.id)

            # Check that broadcast payload only has session_id, status, participant_count
            self.assertTrue(mock_send.called)
            call_args = mock_send.call_args[0]
            payload = call_args[1].get('payload', {})

            self.assertIn('session_id', payload)
            self.assertIn('status', payload)
            self.assertIn('participant_count', payload)
            self.assertNotIn('lat', payload)
            self.assertNotIn('lng', payload)
            self.assertNotIn('coordinates', payload)
            self.assertNotIn('last_location', payload)
