import json
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Friendship
from accounts.logic.friend_service import (
    request_friendship,
    accept_friendship,
    decline_friendship,
    cancel_friendship_request,
    remove_friendship,
    get_friends_for_user,
    get_incoming_requests_for_user,
    get_outgoing_requests_for_user,
    get_friendship_status_between,
    get_friends_presence,
)
from activities.models import (
    ActivityType,
    ActivitySession,
    Participation,
    Badge,
    UserBadge,
    Streak,
)
from activities.logic.privacy_service import (
    resolve_location_visibility,
    generalize_location,
    Visibility,
    are_friends,
)
from activities.services import get_privacy_safe_feature
from activities.logic.pulse_service import get_pulse_now

User = get_user_model()


class FriendsAndPrivacyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create distinct test users
        self.alice = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='password123',
            display_name='Alice Wonderland',
            location_privacy_mode='friends'
        )
        self.bob = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='password123',
            display_name='Bob Builder',
            location_privacy_mode='friends'
        )
        self.charlie = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='password123',
            display_name='Charlie Brown',
            location_privacy_mode='blurred'
        )
        self.dave = User.objects.create_user(
            username='dave',
            email='dave@example.com',
            password='password123',
            display_name='Dave Secret',
            location_privacy_mode='hidden'
        )
        self.eve = User.objects.create_user(
            username='eve',
            email='eve@example.com',
            password='password123',
            display_name='Eve Public',
            location_privacy_mode='exact'
        )

        # Activity types
        self.act_running = ActivityType.objects.create(
            name='Running',
            slug='running',
            icon='🏃',
            color='#FF5722',
            is_active=True
        )

        # Test location (Central Park)
        self.center_lat = 40.7829
        self.center_lng = -73.9654
        self.center_point = Point(self.center_lng, self.center_lat, srid=4326)

    # =========================================================================
    # 1. CANONICAL PAIR CONSTRAINTS & DATA MODEL
    # =========================================================================

    def test_canonical_pair_ordering_and_helper(self):
        """Canonical pair helper always orders lower user ID first and blocks self-pairing."""
        low_user = self.alice if self.alice.id < self.bob.id else self.bob
        high_user = self.bob if self.alice.id < self.bob.id else self.alice

        pair1 = Friendship.get_canonical_pair(self.alice, self.bob)
        pair2 = Friendship.get_canonical_pair(self.bob, self.alice)

        self.assertEqual(pair1, (low_user, high_user))
        self.assertEqual(pair2, (low_user, high_user))

        with self.assertRaises(ValueError):
            Friendship.get_canonical_pair(self.alice, self.alice)

    def test_db_unique_and_check_constraints(self):
        """Database enforces uniqueness on (user_a, user_b) and check constraint user_a < user_b."""
        low_user = self.alice if self.alice.id < self.bob.id else self.bob
        high_user = self.bob if self.alice.id < self.bob.id else self.alice

        Friendship.objects.create(
            user_a=low_user,
            user_b=high_user,
            initiated_by=self.alice,
            status=Friendship.Status.PENDING
        )

        # Duplicate canonical pair fails DB UniqueConstraint
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(
                user_a=low_user,
                user_b=high_user,
                initiated_by=self.bob,
                status=Friendship.Status.PENDING
            )

    # =========================================================================
    # 2. FRIENDSHIP SERVICE LIFECYCLE
    # =========================================================================

    def test_friend_request_lifecycle(self):
        """Complete lifecycle: request -> pending -> accept -> accepted -> remove -> none."""
        # Alice requests Bob
        f, outcome = request_friendship(self.alice, self.bob)
        self.assertEqual(outcome, 'requested')
        self.assertEqual(f.status, Friendship.Status.PENDING)
        self.assertEqual(f.initiated_by, self.alice)

        # Friendship status checks
        self.assertEqual(get_friendship_status_between(self.alice, self.bob), 'pending_outgoing')
        self.assertEqual(get_friendship_status_between(self.bob, self.alice), 'pending_incoming')
        self.assertFalse(are_friends(self.alice, self.bob))

        # Bob accepts
        f_accepted = accept_friendship(self.bob, f.id)
        self.assertEqual(f_accepted.status, Friendship.Status.ACCEPTED)
        self.assertTrue(are_friends(self.alice, self.bob))
        self.assertEqual(get_friendship_status_between(self.alice, self.bob), 'accepted')
        self.assertEqual(get_friendship_status_between(self.bob, self.alice), 'accepted')

        # Friends list
        self.assertIn(self.bob, get_friends_for_user(self.alice))
        self.assertIn(self.alice, get_friends_for_user(self.bob))

        # Remove friendship
        removed = remove_friendship(self.alice, self.bob)
        self.assertTrue(removed)
        self.assertFalse(are_friends(self.alice, self.bob))
        self.assertEqual(get_friendship_status_between(self.alice, self.bob), 'none')

    def test_reciprocal_friend_request_auto_accepts(self):
        """If User A requests User B, and User B requests User A, system auto-accepts."""
        f1, outcome1 = request_friendship(self.alice, self.bob)
        self.assertEqual(outcome1, 'requested')
        self.assertEqual(f1.status, Friendship.Status.PENDING)

        f2, outcome2 = request_friendship(self.bob, self.alice)
        self.assertEqual(outcome2, 'accepted')
        self.assertEqual(f2.status, Friendship.Status.ACCEPTED)
        self.assertTrue(are_friends(self.alice, self.bob))

    def test_duplicate_friend_request_idempotency(self):
        """Repeated friend request returns existing state without error or duplicates."""
        f1, outcome1 = request_friendship(self.alice, self.bob)
        self.assertEqual(outcome1, 'requested')

        f2, outcome2 = request_friendship(self.alice, self.bob)
        self.assertEqual(outcome2, 'already_requested')
        self.assertEqual(f1.id, f2.id)

    def test_unauthorized_accept_and_decline_rejected(self):
        """Initiator cannot accept their own request; third-party cannot accept/decline."""
        f, _ = request_friendship(self.alice, self.bob)

        # Alice cannot accept her own outgoing request
        with self.assertRaises(PermissionDenied):
            accept_friendship(self.alice, f.id)

        # Charlie (uninvolved third party) cannot accept
        with self.assertRaises(PermissionDenied):
            accept_friendship(self.charlie, f.id)

        # Charlie cannot decline
        with self.assertRaises(PermissionDenied):
            decline_friendship(self.charlie, f.id)

    def test_cancel_friend_request(self):
        """Initiator can cancel outgoing request; recipient cannot cancel (must decline)."""
        f, _ = request_friendship(self.alice, self.bob)

        # Bob cannot cancel Alice's request
        with self.assertRaises(PermissionDenied):
            cancel_friendship_request(self.bob, f.id)

        # Alice cancels
        cancelled = cancel_friendship_request(self.alice, f.id)
        self.assertTrue(cancelled)
        self.assertFalse(Friendship.objects.filter(id=f.id).exists())

    # =========================================================================
    # 3. PRIVACY RESOLVER MATRIX (resolve_location_visibility)
    # =========================================================================

    def test_privacy_resolver_full_matrix(self):
        """
        Verifies all branches of the authoritative privacy resolver:
        Hidden, Blurred, Friends, Exact against owner, friend, stranger, and pending.
        """
        # Make Alice and Bob accepted friends
        request_friendship(self.alice, self.bob)
        f_req = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_req.id)

        # Make Alice and Charlie pending friends
        request_friendship(self.alice, self.charlie)

        # --- 1. HIDDEN MODE (Dave) ---
        # Owner -> EXACT
        self.assertEqual(resolve_location_visibility(self.dave, self.dave), Visibility.EXACT)
        # Friend -> HIDDEN
        self.assertEqual(resolve_location_visibility(self.dave, self.bob, privacy_mode='hidden'), Visibility.HIDDEN)
        # Stranger -> HIDDEN
        self.assertEqual(resolve_location_visibility(self.dave, self.charlie), Visibility.HIDDEN)
        # Anonymous -> HIDDEN
        self.assertEqual(resolve_location_visibility(self.dave, None), Visibility.HIDDEN)

        # --- 2. BLURRED MODE (Charlie) ---
        # Owner -> EXACT
        self.assertEqual(resolve_location_visibility(self.charlie, self.charlie), Visibility.EXACT)
        # Friend -> BLURRED
        self.assertEqual(resolve_location_visibility(self.charlie, self.bob, privacy_mode='blurred'), Visibility.BLURRED)
        # Stranger -> BLURRED
        self.assertEqual(resolve_location_visibility(self.charlie, self.dave), Visibility.BLURRED)

        # --- 3. FRIENDS MODE (Alice) ---
        # Owner -> EXACT
        self.assertEqual(resolve_location_visibility(self.alice, self.alice), Visibility.EXACT)
        # Accepted friend (Bob) -> EXACT
        self.assertEqual(resolve_location_visibility(self.alice, self.bob), Visibility.EXACT)
        # Pending friend (Charlie) -> BLURRED
        self.assertEqual(resolve_location_visibility(self.alice, self.charlie), Visibility.BLURRED)
        # Stranger (Dave) -> BLURRED
        self.assertEqual(resolve_location_visibility(self.alice, self.dave), Visibility.BLURRED)
        # Anonymous -> BLURRED
        self.assertEqual(resolve_location_visibility(self.alice, None), Visibility.BLURRED)

        # --- 4. EXACT MODE (Eve) ---
        # Owner -> EXACT
        self.assertEqual(resolve_location_visibility(self.eve, self.eve), Visibility.EXACT)
        # Friend -> EXACT
        self.assertEqual(resolve_location_visibility(self.eve, self.bob, privacy_mode='exact'), Visibility.EXACT)
        # Stranger -> EXACT
        self.assertEqual(resolve_location_visibility(self.eve, self.dave), Visibility.EXACT)

    # =========================================================================
    # 4. MAP & PULSE PRIVACY INTEGRATION
    # =========================================================================

    def test_map_feature_privacy_enforcement(self):
        """Map feature generation strictly abides by resolve_location_visibility."""
        # Friendship: Alice & Bob
        request_friendship(self.alice, self.bob)
        f_req = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_req.id)

        session_alice = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.alice, # Friends mode
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE
        )
        Participation.objects.create(
            session=session_alice,
            user=self.alice,
            status=Participation.Status.ACTIVE
        )

        # Alice viewing her own session -> exact coordinates
        feat_alice = get_privacy_safe_feature(session_alice, self.alice)
        self.assertIsNotNone(feat_alice)
        self.assertEqual(feat_alice['geometry']['coordinates'], [self.center_lng, self.center_lat])

        # Bob (friend) viewing Alice's session -> exact coordinates
        feat_bob = get_privacy_safe_feature(session_alice, self.bob)
        self.assertIsNotNone(feat_bob)
        self.assertEqual(feat_bob['geometry']['coordinates'], [self.center_lng, self.center_lat])

        # Dave (stranger) viewing Alice's session -> generalized/blurred coordinates
        feat_dave = get_privacy_safe_feature(session_alice, self.dave)
        self.assertIsNotNone(feat_dave)
        gen_pt = generalize_location(self.center_point)
        self.assertEqual(feat_dave['geometry']['coordinates'], [gen_pt.x, gen_pt.y])

        # Dave's session (Hidden mode)
        session_dave = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.dave, # Hidden mode
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE
        )
        Participation.objects.create(
            session=session_dave,
            user=self.dave,
            status=Participation.Status.ACTIVE
        )

        # Dave viewing his own hidden session -> visible
        self.assertIsNotNone(get_privacy_safe_feature(session_dave, self.dave))
        # Anyone else viewing Dave's hidden session -> None (omitted)
        self.assertIsNone(get_privacy_safe_feature(session_dave, self.alice))
        self.assertIsNone(get_privacy_safe_feature(session_dave, None))

    def test_pulse_now_privacy_enforcement(self):
        """Pulse Now excludes hidden sessions and adjusts distance precision based on friendship."""
        # Alice & Bob are friends
        request_friendship(self.alice, self.bob)
        f_req = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_req.id)

        session_alice = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.alice,
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE
        )
        Participation.objects.create(
            session=session_alice,
            user=self.alice,
            status=Participation.Status.ACTIVE
        )

        # Dave's hidden session
        session_dave = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.dave, # Hidden
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE
        )
        Participation.objects.create(
            session=session_dave,
            user=self.dave,
            status=Participation.Status.ACTIVE
        )

        # Bob queries Pulse:
        pulse_bob = get_pulse_now(self.bob, lat=self.center_lat, lng=self.center_lng)
        session_ids = [item['session_id'] for item in pulse_bob['items']]
        self.assertIn(str(session_alice.id), session_ids)
        self.assertNotIn(str(session_dave.id), session_ids) # Hidden excluded

        # Bob is friend with Alice -> distance display is exact format (<0.1 mi)
        alice_item = next(item for item in pulse_bob['items'] if item['session_id'] == str(session_alice.id))
        self.assertEqual(alice_item['distance']['display'], '<0.1 mi')

        # Charlie (stranger) queries Pulse:
        pulse_charlie = get_pulse_now(self.charlie, lat=self.center_lat, lng=self.center_lng)
        charlie_alice_item = next(item for item in pulse_charlie['items'] if item['session_id'] == str(session_alice.id))
        # For stranger with Friends privacy mode -> coarse distance bucket
        self.assertEqual(charlie_alice_item['distance']['display'], 'Nearby')

    # =========================================================================
    # 5. USER SEARCH API ENDPOINT
    # =========================================================================

    def test_user_search_api_privacy_and_fields(self):
        """User search only leaks safe public fields and excludes requester."""
        self.client.force_authenticate(user=self.alice)

        # Search for 'Bob'
        res = self.client.get('/api/users/search/?q=bob')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 1)
        user_match = data[0]

        self.assertEqual(user_match['username'], 'bob')
        self.assertEqual(user_match['display_name'], 'Bob Builder')
        self.assertEqual(user_match['current_level'], 1)
        self.assertEqual(user_match['friendship_status'], 'none')

        # CRITICAL: Verify sensitive fields are strictly excluded
        self.assertNotIn('email', user_match)
        self.assertNotIn('location_privacy_mode', user_match)
        self.assertNotIn('password', user_match)
        self.assertNotIn('total_xp', user_match)

        # Search for 'Alice' excludes Alice herself
        res_self = self.client.get('/api/users/search/?q=alice')
        self.assertEqual(res_self.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_self.json()), 0)

        # Unauthenticated search rejected
        self.client.logout()
        res_anon = self.client.get('/api/users/search/?q=bob')
        self.assertEqual(res_anon.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 6. PUBLIC PROFILE API ENDPOINT
    # =========================================================================

    def test_public_profile_api(self):
        """Public profile returns safe stats, badges, streaks, and privacy-gated active session."""
        # Award badge and streak to Bob
        badge = Badge.objects.create(
            slug='first-run',
            name='First Run',
            icon='🏅',
            description='Completed first run'
        )
        UserBadge.objects.create(user=self.bob, badge=badge)
        from django.utils import timezone
        Streak.objects.create(
            user=self.bob,
            current_count=3,
            longest_count=5,
            last_qualified_date=timezone.localtime(timezone.now()).date()
        )

        # Bob starts an active session
        session_bob = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.bob, # Friends mode
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE,
            label='Morning Run'
        )
        Participation.objects.create(
            session=session_bob,
            user=self.bob,
            status=Participation.Status.ACTIVE
        )

        # 1. Charlie (stranger) views Bob's profile
        self.client.force_authenticate(user=self.charlie)
        res = self.client.get(f'/api/users/{self.bob.id}/profile/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(data['user']['username'], 'bob')
        self.assertEqual(data['user']['friendship_status'], 'none')
        self.assertEqual(data['streak']['current'], 3)
        self.assertEqual(data['streak']['longest'], 5)
        self.assertEqual(len(data['badges']), 1)
        self.assertEqual(data['badges'][0]['slug'], 'first-run')

        # Active session for stranger: blurred coordinates
        self.assertIsNotNone(data['active_session'])
        self.assertEqual(data['active_session']['visibility'], Visibility.BLURRED)
        self.assertEqual(data['active_session']['location']['mode'], 'blurred')

        # 2. Alice (friend) views Bob's profile
        request_friendship(self.alice, self.bob)
        f_req = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_req.id)

        self.client.force_authenticate(user=self.alice)
        res_friend = self.client.get(f'/api/users/{self.bob.id}/profile/')
        data_friend = res_friend.json()
        self.assertEqual(data_friend['user']['friendship_status'], 'accepted')
        self.assertEqual(data_friend['active_session']['visibility'], Visibility.EXACT)
        self.assertEqual(data_friend['active_session']['location']['mode'], 'exact')
        self.assertEqual(data_friend['active_session']['location']['lat'], self.center_lat)

        # 3. Hidden user profile: active session is omitted
        session_dave = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.dave, # Hidden mode
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE
        )
        Participation.objects.create(
            session=session_dave,
            user=self.dave,
            status=Participation.Status.ACTIVE
        )

        res_dave = self.client.get(f'/api/users/{self.dave.id}/profile/')
        data_dave = res_dave.json()
        self.assertIsNone(data_dave['active_session'])

    # =========================================================================
    # 7. FRIENDSHIP API ENDPOINTS (REQUEST, ACCEPT, DECLINE, CANCEL, REMOVE)
    # =========================================================================

    def test_friend_request_api_flow(self):
        """End-to-end API test for sending, accepting, declining, cancelling, and removing friends."""
        self.client.force_authenticate(user=self.alice)

        # Self-friending rejected
        res_self = self.client.post('/api/friends/request/', {'user_id': self.alice.id})
        self.assertEqual(res_self.status_code, status.HTTP_400_BAD_REQUEST)

        # Alice sends request to Bob
        res_req = self.client.post('/api/friends/request/', {'user_id': self.bob.id})
        self.assertEqual(res_req.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_req.json()['action_result'], 'requested')
        req_id = res_req.json()['friendship']['id']

        # Bob sees incoming request
        self.client.force_authenticate(user=self.bob)
        res_in = self.client.get('/api/friends/requests/incoming/')
        self.assertEqual(res_in.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_in.json()), 1)
        self.assertEqual(res_in.json()[0]['id'], req_id)

        # Alice sees outgoing request
        self.client.force_authenticate(user=self.alice)
        res_out = self.client.get('/api/friends/requests/outgoing/')
        self.assertEqual(res_out.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_out.json()), 1)

        # Bob accepts
        self.client.force_authenticate(user=self.bob)
        res_acc = self.client.post(f'/api/friends/requests/{req_id}/accept/')
        self.assertEqual(res_acc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_acc.json()['status'], 'accepted')

        # Friends list
        res_friends = self.client.get('/api/friends/')
        self.assertEqual(len(res_friends.json()), 1)
        self.assertEqual(res_friends.json()[0]['username'], 'alice')

        # Remove friend
        res_del = self.client.delete(f'/api/friends/{self.alice.id}/')
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        res_friends_after = self.client.get('/api/friends/')
        self.assertEqual(len(res_friends_after.json()), 0)

    # =========================================================================
    # 8. FRIENDS PRESENCE API ENDPOINT
    # =========================================================================

    def test_friends_presence_api(self):
        """Friends presence surfaces active friend sessions and obeys privacy resolver."""
        # Alice & Bob are friends
        request_friendship(self.alice, self.bob)
        f_req = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_req.id)

        # Bob starts active session
        session_bob = ActivitySession.objects.create(
            activity_type=self.act_running,
            created_by=self.bob,
            location=self.center_point,
            status=ActivitySession.Status.ACTIVE,
            label='Central Park Jog'
        )
        Participation.objects.create(
            session=session_bob,
            user=self.bob,
            status=Participation.Status.ACTIVE
        )

        # Alice checks friends presence
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(f'/api/friends/presence/?lat={self.center_lat}&lng={self.center_lng}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 1)

        item = data[0]
        self.assertEqual(item['friend']['username'], 'bob')
        self.assertEqual(item['activity']['slug'], 'running')
        self.assertEqual(item['label'], 'Central Park Jog')
        self.assertEqual(item['visibility_mode'], Visibility.EXACT)
        self.assertEqual(item['location_display'], '<0.1 mi away')

        # Charlie (not friends with Bob) checks presence -> empty
        self.client.force_authenticate(user=self.charlie)
        res_charlie = self.client.get('/api/friends/presence/')
        self.assertEqual(len(res_charlie.json()), 0)
