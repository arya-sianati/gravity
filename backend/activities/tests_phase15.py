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
    GravityEvent
)
from activities.logic.pulse_service import (
    compute_pulse_score,
    format_privacy_safe_distance,
    get_pulse_now
)

User = get_user_model()

class PulseTestsBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='pw',
            location_privacy_mode='blurred'
        )
        self.client.force_authenticate(user=self.user)

        self.center_lat = 40.748817 # Empire State Building area
        self.center_lng = -73.985428
        self.center_point = Point(self.center_lng, self.center_lat, srid=4326)

        self.act_bball = ActivityType.objects.create(
            name='Basketball',
            slug='basketball',
            icon='🏀',
            color='#FF6B00',
            is_active=True
        )
        self.act_running = ActivityType.objects.create(
            name='Running',
            slug='running',
            icon='🏃',
            color='#00F0FF',
            is_active=True
        )

    def create_session(self, activity_type, creator, location=None, status=ActivitySession.Status.ACTIVE, created_at=None, label=None):
        if location is None:
            location = self.center_point
        session = ActivitySession.objects.create(
            activity_type=activity_type,
            created_by=creator,
            location=location,
            status=status,
            label=label
        )
        if created_at:
            ActivitySession.objects.filter(id=session.id).update(created_at=created_at)
            session.refresh_from_db()
        return session

    def add_participant(self, session, user, status=Participation.Status.ACTIVE, join_method=Participation.JoinMethod.SELF):
        return Participation.objects.create(
            session=session,
            user=user,
            status=status,
            join_method=join_method
        )


class PulsePrivacyTests(PulseTestsBase):
    def setUp(self):
        super().setUp()
        self.creator_exact = User.objects.create_user(
            username='exact_user', email='exact@example.com', password='pw', location_privacy_mode='exact'
        )
        self.creator_blurred = User.objects.create_user(
            username='blurred_user', email='blurred@example.com', password='pw', location_privacy_mode='blurred'
        )
        self.creator_hidden = User.objects.create_user(
            username='hidden_user', email='hidden@example.com', password='pw', location_privacy_mode='hidden'
        )
        self.creator_friends = User.objects.create_user(
            username='friends_user', email='friends@example.com', password='pw', location_privacy_mode='friends'
        )

    def test_exact_session_appears(self):
        # 1. Exact session appears according to policy
        s = self.create_session(self.act_bball, self.creator_exact)
        self.add_participant(s, self.creator_exact)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item_ids = [item['session_id'] for item in res.data['items']]
        self.assertIn(str(s.id), item_ids)

    def test_blurred_session_appears_without_raw_exact_coordinate(self):
        # 2. Blurred session appears without raw exact coordinate
        s = self.create_session(self.act_bball, self.creator_blurred)
        self.add_participant(s, self.creator_blurred)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        self.assertNotIn('location', item)
        self.assertNotIn('coordinates', item)
        self.assertNotIn('lat', item)
        self.assertNotIn('lng', item)

    def test_pulse_response_contains_no_exact_raw_coordinate_field(self):
        # 3. Pulse response contains no exact raw coordinate field
        s = self.create_session(self.act_bball, self.creator_exact)
        self.add_participant(s, self.creator_exact)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        for it in res.data['items']:
            self.assertNotIn('latitude', it)
            self.assertNotIn('longitude', it)
            self.assertNotIn('lat', it)
            self.assertNotIn('lng', it)
            self.assertNotIn('raw_coordinates', it)

    def test_hidden_session_omitted_for_non_owner(self):
        # 4. Hidden session omitted
        s = self.create_session(self.act_bball, self.creator_hidden)
        self.add_participant(s, self.creator_hidden)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item_ids = [item['session_id'] for item in res.data['items']]
        self.assertNotIn(str(s.id), item_ids)

        # But if the owner itself queries, they can see their own session
        client_owner = APIClient()
        client_owner.force_authenticate(user=self.creator_hidden)
        res_owner = client_owner.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res_owner.status_code, 200)
        owner_item_ids = [item['session_id'] for item in res_owner.data['items']]
        self.assertIn(str(s.id), owner_item_ids)

    def test_friends_only_fallback_remains_safe(self):
        # 5. Friends-only fallback remains safe before Phase 16 (blurred)
        s = self.create_session(self.act_bball, self.creator_friends)
        self.add_participant(s, self.creator_friends)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        self.assertIn(item['distance']['display'], ["Nearby", "<0.5 mi", "~1 mi"])

    def test_blurred_distance_does_not_expose_excessive_precision(self):
        # 6. Blurred distance does not expose excessive precision (e.g. 183.27 meters)
        # Point ~250 meters away
        loc_250m = Point(self.center_lng + 0.002, self.center_lat, srid=4326)
        s = self.create_session(self.act_bball, self.creator_blurred, location=loc_250m)
        self.add_participant(s, self.creator_blurred)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        disp = item['distance']['display']
        # Distance display should be coarse bucket like "Nearby" or "<0.5 mi", never a high-precision float string
        self.assertTrue(disp in ["Nearby", "<0.5 mi", "~1 mi"] or disp.endswith("mi"))
        self.assertFalse("meters" in disp)
        self.assertFalse("." in disp and len(disp.split(".")[1].split()[0]) > 1) # No 2+ decimal places

    def test_participant_identities_and_creator_details_omitted(self):
        # 7 & 8. Participant identities & creator email/username omitted
        s = self.create_session(self.act_bball, self.creator_exact)
        self.add_participant(s, self.creator_exact)
        other_user = User.objects.create_user(username='other_guy', email='secret@example.com', password='pw')
        self.add_participant(s, other_user)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        self.assertNotIn('participants', item)
        self.assertNotIn('users', item)
        self.assertNotIn('created_by', item)
        self.assertNotIn('creator', item)
        self.assertNotIn('email', item)
        self.assertNotIn('username', item)


class PulseAPITests(PulseTestsBase):
    def setUp(self):
        super().setUp()
        self.creator = User.objects.create_user(
            username='host_user', email='host@example.com', password='pw', location_privacy_mode='exact'
        )

    def test_nearby_active_session_returned_and_far_omitted(self):
        # 1. Nearby active session returned, 2. Far session omitted
        # Close session (100m away)
        s_near = self.create_session(self.act_bball, self.creator, location=self.center_point)
        self.add_participant(s_near, self.creator)

        # Far session (~100km away: lat + 1.0 degree)
        creator_far = User.objects.create_user(username='creator_far', password='pw')
        far_point = Point(self.center_lng, self.center_lat + 1.0, srid=4326)
        s_far = self.create_session(self.act_bball, creator_far, location=far_point)
        self.add_participant(s_far, creator_far)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&radius=5000')
        self.assertEqual(res.status_code, 200)
        item_ids = [it['session_id'] for it in res.data['items']]
        self.assertIn(str(s_near.id), item_ids)
        self.assertNotIn(str(s_far.id), item_ids)

    def test_ended_and_cancelled_sessions_omitted(self):
        # 3. Ended session omitted, 4. Cancelled session omitted
        creator_ended = User.objects.create_user(username='creator_ended', password='pw')
        s_ended = self.create_session(self.act_bball, creator_ended, status=ActivitySession.Status.ENDED)
        self.add_participant(s_ended, creator_ended, status=Participation.Status.COMPLETED)

        creator_canc = User.objects.create_user(username='creator_canc', password='pw')
        s_cancelled = self.create_session(self.act_bball, creator_canc, status=ActivitySession.Status.CANCELLED)
        self.add_participant(s_cancelled, creator_canc, status=Participation.Status.LEFT)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item_ids = [it['session_id'] for it in res.data['items']]
        self.assertNotIn(str(s_ended.id), item_ids)
        self.assertNotIn(str(s_cancelled.id), item_ids)

    def test_disabled_activity_type_omitted(self):
        # 5. Disabled Activity Type omitted
        act_disabled = ActivityType.objects.create(name='DisabledAct', slug='disabled-act', is_active=False)
        s = self.create_session(act_disabled, self.creator)
        self.add_participant(s, self.creator)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item_ids = [it['session_id'] for it in res.data['items']]
        self.assertNotIn(str(s.id), item_ids)

    def test_zero_active_participants_session_omitted(self):
        # 6. Zero active participant session omitted
        s = self.create_session(self.act_bball, self.creator)
        # Add participant that already left
        self.add_participant(s, self.creator, status=Participation.Status.LEFT)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item_ids = [it['session_id'] for it in res.data['items']]
        self.assertNotIn(str(s.id), item_ids)

    def test_correct_active_participant_count(self):
        # 7. Correct active participant count
        s = self.create_session(self.act_bball, self.creator)
        self.add_participant(s, self.creator, status=Participation.Status.ACTIVE)
        u2 = User.objects.create_user(username='p2', password='pw')
        self.add_participant(s, u2, status=Participation.Status.ACTIVE)
        u3 = User.objects.create_user(username='p3', password='pw')
        self.add_participant(s, u3, status=Participation.Status.LEFT) # should not count

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        self.assertEqual(item['participant_count'], 2)

    def test_activity_filter(self):
        # 8. Activity filter
        s_bb = self.create_session(self.act_bball, self.creator)
        self.add_participant(s_bb, self.creator)

        creator_run = User.objects.create_user(username='creator_run', password='pw')
        s_run = self.create_session(self.act_running, creator_run)
        self.add_participant(s_run, creator_run)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&activity=running')
        self.assertEqual(res.status_code, 200)
        item_ids = [it['session_id'] for it in res.data['items']]
        self.assertIn(str(s_run.id), item_ids)
        self.assertNotIn(str(s_bb.id), item_ids)

    def test_radius_default_and_clamping(self):
        # 9. Default radius, 10. Max radius clamping
        # Session at 3km
        loc_3km = Point(self.center_lng + 0.025, self.center_lat, srid=4326)
        s_3km = self.create_session(self.act_bball, self.creator, location=loc_3km)
        self.add_participant(s_3km, self.creator)

        # Default radius is 5000m -> 3km session appears
        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['search_radius_m'], 5000.0)
        self.assertIn(str(s_3km.id), [it['session_id'] for it in res.data['items']])

        # Radius 1000m -> 3km session omitted
        res_small = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&radius=1000')
        self.assertEqual(res_small.data['search_radius_m'], 1000.0)
        self.assertNotIn(str(s_3km.id), [it['session_id'] for it in res_small.data['items']])

        # Pathological giant radius clamped to 50000m
        res_clamp = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&radius=9999999')
        self.assertEqual(res_clamp.status_code, 200)
        self.assertEqual(res_clamp.data['search_radius_m'], 50000.0)

    def test_invalid_parameters_rejected(self):
        # 11. Invalid lat, 12. Invalid lng, 13. Invalid radius, 14. Limit handling
        # Missing lat/lng
        r1 = self.client.get('/api/pulse/now/')
        self.assertEqual(r1.status_code, 400)

        # Invalid lat
        r2 = self.client.get(f'/api/pulse/now/?lat=999&lng={self.center_lng}')
        self.assertEqual(r2.status_code, 400)

        # Invalid lng
        r3 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng=abc')
        self.assertEqual(r3.status_code, 400)

        # Invalid radius
        r4 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&radius=-5')
        self.assertEqual(r4.status_code, 400)

        r5 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&radius=zero')
        self.assertEqual(r5.status_code, 400)

        # Limit handling
        s = self.create_session(self.act_bball, self.creator)
        self.add_participant(s, self.creator)
        r6 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&limit=1')
        self.assertEqual(r6.status_code, 200)
        self.assertLessEqual(len(r6.data['items']), 1)


class PulseScoringTests(PulseTestsBase):
    def setUp(self):
        super().setUp()
        self.creator = User.objects.create_user(
            username='score_host', password='pw', location_privacy_mode='exact'
        )

    def test_scoring_factors(self):
        # 16. Participant strength affects score, 17. Distance affects score, 18. Recency affects score
        now = timezone.now()
        base_time = now - timedelta(minutes=10)

        # Distance: closer has higher score
        score_close = compute_pulse_score(distance_m=200, participant_count=5, started_at=base_time, now=now, radius_m=5000)
        score_far = compute_pulse_score(distance_m=3000, participant_count=5, started_at=base_time, now=now, radius_m=5000)
        self.assertGreater(score_close, score_far)

        # Participant: more participants has higher score
        score_more_ppl = compute_pulse_score(distance_m=500, participant_count=12, started_at=base_time, now=now, radius_m=5000)
        score_few_ppl = compute_pulse_score(distance_m=500, participant_count=2, started_at=base_time, now=now, radius_m=5000)
        self.assertGreater(score_more_ppl, score_few_ppl)

        # Recency: newer has higher score
        score_recent = compute_pulse_score(distance_m=500, participant_count=5, started_at=now - timedelta(minutes=5), now=now, radius_m=5000)
        score_old = compute_pulse_score(distance_m=500, participant_count=5, started_at=now - timedelta(minutes=120), now=now, radius_m=5000)
        self.assertGreater(score_recent, score_old)

    def test_deterministic_tie_ordering(self):
        # 15. Deterministic ordering: when scores tie, secondary tie-breakers apply
        # Create two sessions with identical score inputs (distance 500m, 5 participants, same start time)
        now = timezone.now()
        creator2 = User.objects.create_user(username='score_host2', password='pw', location_privacy_mode='exact')
        s1 = self.create_session(self.act_bball, self.creator, created_at=now - timedelta(minutes=10))
        s2 = self.create_session(self.act_running, creator2, created_at=now - timedelta(minutes=10))
        for i in range(5):
            u1 = User.objects.create_user(username=f'u1_{now.timestamp()}_{i}', password='pw')
            u2 = User.objects.create_user(username=f'u2_{now.timestamp()}_{i}', password='pw')
            self.add_participant(s1, u1)
            self.add_participant(s2, u2)

        res1 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        res2 = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')

        order1 = [it['session_id'] for it in res1.data['items']]
        order2 = [it['session_id'] for it in res2.data['items']]
        self.assertEqual(order1, order2) # 100% deterministic between refetches


class PulseJoinTests(PulseTestsBase):
    def setUp(self):
        super().setUp()
        self.host = User.objects.create_user(
            username='join_host', password='pw', location_privacy_mode='exact'
        )
        self.session = self.create_session(self.act_bball, self.host)
        self.add_participant(self.session, self.host)

    def test_join_from_pulse_uses_suggestion_method(self):
        # Joining with source=pulse sets join_method=suggestion
        res = self.client.post(f'/api/sessions/{self.session.id}/join/', {'source': 'pulse'}, format='json')
        self.assertEqual(res.status_code, 200)

        part = Participation.objects.get(session=self.session, user=self.user)
        self.assertEqual(part.status, Participation.Status.ACTIVE)
        self.assertEqual(part.join_method, Participation.JoinMethod.SUGGESTION)

    def test_one_active_participation_constraint(self):
        # User already active in another session receives 409 Conflict
        s_other = self.create_session(self.act_running, self.host)
        self.add_participant(s_other, self.user, status=Participation.Status.ACTIVE)

        res = self.client.post(f'/api/sessions/{self.session.id}/join/', {'source': 'pulse'}, format='json')
        self.assertEqual(res.status_code, 409)

    def test_ended_session_cannot_be_joined(self):
        self.session.status = ActivitySession.Status.ENDED
        self.session.save()

        res = self.client.post(f'/api/sessions/{self.session.id}/join/', {'source': 'pulse'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_participant_count_changes_after_join(self):
        # Pulse refetch reflects incremented count
        res_before = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item_before = next(it for it in res_before.data['items'] if it['session_id'] == str(self.session.id))
        count_before = item_before['participant_count']
        self.assertEqual(count_before, 1)

        # Join
        self.client.post(f'/api/sessions/{self.session.id}/join/', {'source': 'pulse'}, format='json')

        # Refetch
        res_after = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item_after = next(it for it in res_after.data['items'] if it['session_id'] == str(self.session.id))
        self.assertEqual(item_after['participant_count'], 2)


class PulseDynamicActivityTests(PulseTestsBase):
    def setUp(self):
        super().setUp()
        self.host = User.objects.create_user(
            username='pickle_host', password='pw', location_privacy_mode='exact'
        )

    def test_dynamic_activity_pickleball(self):
        # Dynamic Activity (Pickleball) created at runtime
        act_pb = ActivityType.objects.create(
            name='Pickleball',
            slug='pickleball',
            icon='🏓',
            color='#10B981',
            is_active=True
        )
        s_pb = self.create_session(act_pb, self.host)
        self.add_participant(s_pb, self.host)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, 200)
        item = next((it for it in res.data['items'] if it['session_id'] == str(s_pb.id)), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['activity']['slug'], 'pickleball')
        self.assertEqual(item['activity']['name'], 'Pickleball')
        self.assertEqual(item['activity']['icon'], '🏓')
        self.assertEqual(item['activity']['color'], '#10B981')

        # Filter by pickleball
        res_filtered = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}&activity=pickleball')
        self.assertEqual(len(res_filtered.data['items']), 1)
        self.assertEqual(res_filtered.data['items'][0]['session_id'], str(s_pb.id))

    def test_other_activity_with_label(self):
        act_other = ActivityType.objects.create(
            name='Other',
            slug='other',
            icon='✨',
            color='#9CA3AF',
            is_active=True
        )
        s_custom = self.create_session(act_other, self.host, label='Ultimate Frisbee')
        self.add_participant(s_custom, self.host)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item = next(it for it in res.data['items'] if it['session_id'] == str(s_custom.id))
        self.assertEqual(item['activity']['slug'], 'other')
        self.assertEqual(item['label'], 'Ultimate Frisbee')

    def test_event_badge_indicator(self):
        # Match live event
        now = timezone.now()
        event = GravityEvent.objects.create(
            name='Pickleball Frenzy',
            slug='pb-frenzy',
            activity_type=self.act_bball,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            is_active=True,
            xp_multiplier=2.0,
            flat_xp_bonus=50
        )
        s = self.create_session(self.act_bball, self.host)
        self.add_participant(s, self.host)

        res = self.client.get(f'/api/pulse/now/?lat={self.center_lat}&lng={self.center_lng}')
        item = next(it for it in res.data['items'] if it['session_id'] == str(s.id))
        self.assertIsNotNone(item['event'])
        self.assertEqual(item['event']['name'], 'Pickleball Frenzy')
        self.assertEqual(item['event']['xp_multiplier'], 2.0)
