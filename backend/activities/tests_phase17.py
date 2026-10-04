from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Friendship
from accounts.logic.friend_service import request_friendship, accept_friendship, remove_friendship
from activities.models import (
    ActivityType,
    ActivityMetric,
    ActivitySession,
    Participation,
    MetricValue,
    FriendChallenge,
    ChallengeParticipant,
    ChallengeReward,
    XPTransaction,
)
from activities.logic.challenge_service import (
    create_challenge,
    accept_challenge_invitation,
    decline_challenge_invitation,
    cancel_challenge,
    calculate_and_update_challenge_progress,
    distribute_challenge_rewards,
    DEFAULT_CHALLENGE_PARTICIPATION_XP,
    DEFAULT_CHALLENGE_WIN_XP,
)
from activities.logic.privacy_service import resolve_location_visibility, Visibility

User = get_user_model()


class FriendChallengesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.alice = User.objects.create_user(
            username='alice', email='alice@example.com', password='pw',
            display_name='Alice Wonderland', location_privacy_mode='friends'
        )
        self.bob = User.objects.create_user(
            username='bob', email='bob@example.com', password='pw',
            display_name='Bob Builder', location_privacy_mode='friends'
        )
        self.charlie = User.objects.create_user(
            username='charlie', email='charlie@example.com', password='pw',
            display_name='Charlie Brown', location_privacy_mode='blurred'
        )
        self.dave = User.objects.create_user(
            username='dave', email='dave@example.com', password='pw',
            display_name='Dave Stranger', location_privacy_mode='hidden'
        )

        # Alice & Bob are accepted friends
        request_friendship(self.alice, self.bob)
        f_ab = Friendship.objects.filter(initiated_by=self.alice).first()
        accept_friendship(self.bob, f_ab.id)

        # Alice & Charlie are accepted friends
        request_friendship(self.alice, self.charlie)
        f_ac = Friendship.objects.filter(initiated_by=self.alice, status=Friendship.Status.PENDING).first()
        accept_friendship(self.charlie, f_ac.id)

        # Dave is a stranger (no friendship)

        # Activity Types & Metrics
        self.act_running = ActivityType.objects.create(
            name='Running', slug='running', icon='🏃', color='#FF5722', is_active=True
        )
        self.metric_dist = ActivityMetric.objects.create(
            activity_type=self.act_running, name='Distance', slug='distance',
            unit='mi', data_type=ActivityMetric.DataType.DECIMAL,
            aggregation=ActivityMetric.AggregationMode.SUM, is_primary=True
        )

        self.act_bball = ActivityType.objects.create(
            name='Basketball', slug='basketball', icon='🏀', color='#FF9800', is_active=True
        )
        self.metric_points = ActivityMetric.objects.create(
            activity_type=self.act_bball, name='Points', slug='points',
            unit='pts', data_type=ActivityMetric.DataType.INTEGER,
            aggregation=ActivityMetric.AggregationMode.SUM, is_primary=True
        )

        # Dynamic Activity (Pickleball)
        self.act_pickleball = ActivityType.objects.create(
            name='Pickleball', slug='pickleball', icon='🏓', color='#4CAF50', is_active=True
        )
        self.metric_games_won = ActivityMetric.objects.create(
            activity_type=self.act_pickleball, name='Games Won', slug='games_won',
            unit='wins', data_type=ActivityMetric.DataType.INTEGER,
            aggregation=ActivityMetric.AggregationMode.SUM, is_primary=True
        )

        self.now = timezone.now()
        self.start_time = self.now - timedelta(hours=1)
        self.end_time = self.now + timedelta(days=2)

    # =========================================================================
    # 1. SECURITY & INVITATION AUTHORIZATION
    # =========================================================================

    def test_cannot_invite_self(self):
        """User cannot invite themselves as an invited participant."""
        with self.assertRaises(ValidationError):
            create_challenge(
                creator=self.alice,
                activity_type=self.act_running,
                metric=self.metric_dist,
                challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                target_value=10.0,
                starts_at=self.start_time,
                ends_at=self.end_time,
                invitee_ids=[self.alice.id]
            )

    def test_stranger_cannot_be_invited(self):
        """Cannot invite a user who is not an accepted friend."""
        with self.assertRaises(ValidationError) as ctx:
            create_challenge(
                creator=self.alice,
                activity_type=self.act_running,
                metric=self.metric_dist,
                challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                target_value=10.0,
                starts_at=self.start_time,
                ends_at=self.end_time,
                invitee_ids=[self.dave.id]
            )
        self.assertIn("not an accepted friend", str(ctx.exception))

    def test_pending_friend_cannot_be_invited(self):
        """Cannot invite a pending friend who has not accepted yet."""
        eve = User.objects.create_user(username='eve', password='pw')
        request_friendship(self.alice, eve) # pending only

        with self.assertRaises(ValidationError):
            create_challenge(
                creator=self.alice,
                activity_type=self.act_running,
                metric=self.metric_dist,
                challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                target_value=10.0,
                starts_at=self.start_time,
                ends_at=self.end_time,
                invitee_ids=[eve.id]
            )

    def test_accepted_friend_can_be_invited(self):
        """Accepted friend is invited successfully."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )
        self.assertEqual(ch.participants.count(), 2)
        creator_p = ch.participants.get(user=self.alice)
        bob_p = ch.participants.get(user=self.bob)
        self.assertEqual(creator_p.invitation_status, ChallengeParticipant.InvitationStatus.ACCEPTED)
        self.assertEqual(bob_p.invitation_status, ChallengeParticipant.InvitationStatus.INVITED)

    def test_unrelated_user_cannot_view_or_accept(self):
        """Stranger cannot view or accept an invite for a private challenge."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )

        # Dave is unrelated
        self.client.force_authenticate(user=self.dave)
        res_view = self.client.get(f'/api/challenges/{ch.id}/')
        self.assertEqual(res_view.status_code, status.HTTP_403_FORBIDDEN)

        res_accept = self.client.post(f'/api/challenges/{ch.id}/accept/')
        self.assertEqual(res_accept.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_creator_cannot_cancel(self):
        """Only the challenge creator can cancel."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )

        self.client.force_authenticate(user=self.bob)
        res = self.client.post(f'/api/challenges/{ch.id}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 2. MODEL VALIDATION & LIFECYCLE
    # =========================================================================

    def test_invalid_metric_activity_combination_rejected(self):
        """Metric must belong to the selected activity type."""
        with self.assertRaises(ValidationError):
            create_challenge(
                creator=self.alice,
                activity_type=self.act_bball,
                metric=self.metric_dist, # Running metric on Basketball!
                challenge_type=FriendChallenge.ChallengeType.HIGHEST_BY_DEADLINE,
                target_value=None,
                starts_at=self.start_time,
                ends_at=self.end_time,
                invitee_ids=[self.bob.id]
            )

    def test_invalid_time_window_rejected(self):
        """starts_at must be before ends_at."""
        with self.assertRaises(ValidationError):
            create_challenge(
                creator=self.alice,
                activity_type=self.act_running,
                metric=self.metric_dist,
                challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                target_value=10.0,
                starts_at=self.end_time,
                ends_at=self.start_time, # inverted
                invitee_ids=[self.bob.id]
            )

    def test_target_value_validation(self):
        """target_value must be > 0 for First to Target and Cooperative Target."""
        with self.assertRaises(ValidationError):
            create_challenge(
                creator=self.alice,
                activity_type=self.act_running,
                metric=self.metric_dist,
                challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
                target_value=0, # invalid
                starts_at=self.start_time,
                ends_at=self.end_time,
                invitee_ids=[self.bob.id]
            )

    def test_invitation_lifecycle_and_declining(self):
        """When an invitee accepts, challenge activates; if all decline, challenge cancels."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )
        self.assertEqual(ch.status, FriendChallenge.Status.PENDING)

        # Bob declines
        decline_challenge_invitation(self.bob, ch.id)
        ch.refresh_from_db()
        # All invitees declined -> auto-cancelled
        self.assertEqual(ch.status, FriendChallenge.Status.CANCELLED)

    # =========================================================================
    # 3. FIRST TO TARGET
    # =========================================================================

    def test_first_to_target_progression_and_winner(self):
        """First participant to reach target wins, challenge completes, rewards distributed."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )
        accept_challenge_invitation(self.bob, ch.id)
        ch.refresh_from_db()
        self.assertEqual(ch.status, FriendChallenge.Status.ACTIVE)

        # 1. Alice runs 6 miles (below target)
        s1 = ActivitySession.objects.create(
            activity_type=self.act_running, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p1 = Participation.objects.create(
            session=s1, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=10),
            left_at=self.start_time + timedelta(minutes=50)
        )
        MetricValue.objects.create(participation=p1, metric=self.metric_dist, value=6.0)

        calculate_and_update_challenge_progress(ch)
        ch.refresh_from_db()
        self.assertEqual(ch.status, FriendChallenge.Status.ACTIVE)
        self.assertIsNone(ch.winner)
        alice_part = ch.participants.get(user=self.alice)
        self.assertEqual(alice_part.progress, 6.0)

        # 2. Bob runs 12 miles (exceeds target first!)
        s2 = ActivitySession.objects.create(
            activity_type=self.act_running, created_by=self.bob,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p2 = Participation.objects.create(
            session=s2, user=self.bob, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=20),
            left_at=self.start_time + timedelta(minutes=80)
        )
        MetricValue.objects.create(participation=p2, metric=self.metric_dist, value=12.0)

        calculate_and_update_challenge_progress(ch)
        ch.refresh_from_db()

        self.assertEqual(ch.status, FriendChallenge.Status.COMPLETED)
        self.assertEqual(ch.winner, self.bob)
        bob_part = ch.participants.get(user=self.bob)
        self.assertTrue(bob_part.is_winner)
        self.assertEqual(bob_part.rank, 1)

        # Verify XP rewards: Bob (winner) gets Win + Completion XP; Alice gets Completion XP
        self.bob.refresh_from_db()
        self.alice.refresh_from_db()
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.bob).count(), 2)
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.alice).count(), 1)

        # 3. Subsequent runs by Alice do NOT change winner
        s3 = ActivitySession.objects.create(
            activity_type=self.act_running, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p3 = Participation.objects.create(
            session=s3, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(hours=2),
            left_at=self.start_time + timedelta(hours=3)
        )
        MetricValue.objects.create(participation=p3, metric=self.metric_dist, value=15.0)

        calculate_and_update_challenge_progress(ch)
        ch.refresh_from_db()
        self.assertEqual(ch.winner, self.bob) # Still Bob!

    # =========================================================================
    # 4. HIGHEST BY DEADLINE
    # =========================================================================

    def test_highest_by_deadline_and_ties(self):
        """Highest metric wins at deadline; ties produce co-winners with competition ranking."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_bball,
            metric=self.metric_points,
            challenge_type=FriendChallenge.ChallengeType.HIGHEST_BY_DEADLINE,
            target_value=None,
            starts_at=self.start_time,
            ends_at=self.start_time + timedelta(hours=3),
            invitee_ids=[self.bob.id, self.charlie.id]
        )
        accept_challenge_invitation(self.bob, ch.id)
        accept_challenge_invitation(self.charlie, ch.id)

        # Alice scores 30 points
        s_a = ActivitySession.objects.create(
            activity_type=self.act_bball, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p_a = Participation.objects.create(
            session=s_a, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=10)
        )
        MetricValue.objects.create(participation=p_a, metric=self.metric_points, value=30.0)

        # Bob scores 30 points (Tied for first!)
        s_b = ActivitySession.objects.create(
            activity_type=self.act_bball, created_by=self.bob,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p_b = Participation.objects.create(
            session=s_b, user=self.bob, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=20)
        )
        MetricValue.objects.create(participation=p_b, metric=self.metric_points, value=30.0)

        # Charlie scores 15 points
        s_c = ActivitySession.objects.create(
            activity_type=self.act_bball, created_by=self.charlie,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p_c = Participation.objects.create(
            session=s_c, user=self.charlie, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=30)
        )
        MetricValue.objects.create(participation=p_c, metric=self.metric_points, value=15.0)

        # Evaluate at deadline
        deadline_time = self.start_time + timedelta(hours=4)
        calculate_and_update_challenge_progress(ch, now=deadline_time)
        ch.refresh_from_db()

        self.assertEqual(ch.status, FriendChallenge.Status.COMPLETED)
        p_alice = ch.participants.get(user=self.alice)
        p_bob = ch.participants.get(user=self.bob)
        p_charlie = ch.participants.get(user=self.charlie)

        # Competition ranking: Alice=1, Bob=1, Charlie=3!
        self.assertEqual(p_alice.rank, 1)
        self.assertEqual(p_bob.rank, 1)
        self.assertEqual(p_charlie.rank, 3)
        self.assertTrue(p_alice.is_winner)
        self.assertTrue(p_bob.is_winner)
        self.assertFalse(p_charlie.is_winner)

        # Both co-winners get Winner XP + Completion XP
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.alice, reward_type='winner').count(), 1)
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.bob, reward_type='winner').count(), 1)
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.charlie, reward_type='winner').count(), 0)
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.charlie, reward_type='completion').count(), 1)

    # =========================================================================
    # 5. COOPERATIVE TARGET
    # =========================================================================

    def test_cooperative_target(self):
        """All participants contribute toward combined target; completes when sum reaches target."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.COOPERATIVE_TARGET,
            target_value=20.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )
        accept_challenge_invitation(self.bob, ch.id)

        # Alice runs 8 miles
        s1 = ActivitySession.objects.create(
            activity_type=self.act_running, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p1 = Participation.objects.create(
            session=s1, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=10)
        )
        MetricValue.objects.create(participation=p1, metric=self.metric_dist, value=8.0)

        # Bob runs 12 miles -> Combined = 20.0 (Target met!)
        s2 = ActivitySession.objects.create(
            activity_type=self.act_running, created_by=self.bob,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p2 = Participation.objects.create(
            session=s2, user=self.bob, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=20)
        )
        MetricValue.objects.create(participation=p2, metric=self.metric_dist, value=12.0)

        calculate_and_update_challenge_progress(ch)
        ch.refresh_from_db()

        self.assertEqual(ch.status, FriendChallenge.Status.COMPLETED)
        self.assertIsNone(ch.winner) # No individual winner in cooperative mode
        self.assertEqual(ch.participants.get(user=self.alice).progress, 8.0)
        self.assertEqual(ch.participants.get(user=self.bob).progress, 12.0)

        # Both get completion XP
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.alice).count(), 1)
        self.assertEqual(ChallengeReward.objects.filter(challenge=ch, user=self.bob).count(), 1)

    # =========================================================================
    # 6. DYNAMIC ACTIVITY ACCEPTANCE (PICKLEBALL)
    # =========================================================================

    def test_dynamic_pickleball_first_to_5_wins(self):
        """Dynamic activity acceptance using Pickleball without any hard-coded rules."""
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_pickleball,
            metric=self.metric_games_won,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=5.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id],
            title='First to 5 Pickleball Wins'
        )
        accept_challenge_invitation(self.bob, ch.id)

        # Session 1: Alice wins 3 games
        s1 = ActivitySession.objects.create(
            activity_type=self.act_pickleball, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p1 = Participation.objects.create(
            session=s1, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=15)
        )
        MetricValue.objects.create(participation=p1, metric=self.metric_games_won, value=3.0)

        # Session 2: Alice wins 2 more games -> Total = 5 (Target met!)
        s2 = ActivitySession.objects.create(
            activity_type=self.act_pickleball, created_by=self.alice,
            location=Point(0, 0, srid=4326), status=ActivitySession.Status.ENDED
        )
        p2 = Participation.objects.create(
            session=s2, user=self.alice, status=Participation.Status.COMPLETED,
            joined_at=self.start_time + timedelta(minutes=45)
        )
        MetricValue.objects.create(participation=p2, metric=self.metric_games_won, value=2.0)

        calculate_and_update_challenge_progress(ch)
        ch.refresh_from_db()

        self.assertEqual(ch.status, FriendChallenge.Status.COMPLETED)
        self.assertEqual(ch.winner, self.alice)
        self.assertEqual(ch.participants.get(user=self.alice).progress, 5.0)

    # =========================================================================
    # 7. FRIEND REMOVAL & PRIVACY ISOLATION
    # =========================================================================

    def test_friend_removal_behavior_and_location_privacy_isolation(self):
        """
        If friendship is removed after a challenge starts:
        - Challenge continues to completion and history is preserved.
        - Location visibility immediately revokes exact friends-mode access.
        - Challenge participation NEVER bypasses location privacy!
        """
        ch = create_challenge(
            creator=self.alice,
            activity_type=self.act_running,
            metric=self.metric_dist,
            challenge_type=FriendChallenge.ChallengeType.FIRST_TO_TARGET,
            target_value=10.0,
            starts_at=self.start_time,
            ends_at=self.end_time,
            invitee_ids=[self.bob.id]
        )
        accept_challenge_invitation(self.bob, ch.id)

        # Verify while friends, Bob sees Alice's location as EXACT
        self.assertEqual(resolve_location_visibility(self.alice, self.bob), Visibility.EXACT)

        # Now Alice removes Bob from friends
        remove_friendship(self.alice, self.bob)

        # CRITICAL PRIVACY TEST:
        # Challenge participation must NOT bypass location privacy!
        # Since they are no longer friends, Alice's Friends-mode location becomes BLURRED for Bob!
        self.assertEqual(resolve_location_visibility(self.alice, self.bob), Visibility.BLURRED)

        # Historical challenge remains valid and accessible to participants
        self.client.force_authenticate(user=self.bob)
        res = self.client.get(f'/api/challenges/{ch.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['id'], ch.id)

    # =========================================================================
    # 8. API ENDPOINTS INTEGRATION
    # =========================================================================

    def test_challenge_api_endpoints_flow(self):
        """End-to-end API test for creating, listing, accepting, and viewing detail."""
        self.client.force_authenticate(user=self.alice)

        # Create challenge via API
        payload = {
            "activity_type": "running",
            "metric": "distance",
            "challenge_type": "first_to_target",
            "target_value": 15.0,
            "starts_at": self.start_time.isoformat(),
            "ends_at": self.end_time.isoformat(),
            "invitees": [self.bob.id],
            "title": "Weekend 15M Sprint"
        }
        res_create = self.client.post('/api/challenges/', payload, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        ch_id = res_create.json()['id']

        # Bob views his challenges
        self.client.force_authenticate(user=self.bob)
        res_list = self.client.get('/api/challenges/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.json()), 1)
        self.assertEqual(res_list.json()[0]['id'], ch_id)

        # Bob accepts invitation via API
        res_accept = self.client.post(f'/api/challenges/{ch_id}/accept/')
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.json()['status'], 'active')

        # Alice views challenge detail
        self.client.force_authenticate(user=self.alice)
        res_detail = self.client.get(f'/api/challenges/{ch_id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        data = res_detail.json()
        self.assertEqual(data['title'], 'Weekend 15M Sprint')
        self.assertEqual(len(data['participants']), 2)
