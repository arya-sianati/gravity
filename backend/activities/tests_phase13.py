from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import GravityEvent, EventReward, ActivityType, ActivitySession, Participation, Badge, XPTransaction
from .logic.event_service import evaluate_events_for_participation
from datetime import timedelta
import io

User = get_user_model()

class EventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pw')
        self.user2 = User.objects.create_user(username='tester2', password='pw')
        
        self.act_bball = ActivityType.objects.create(name='Basketball', slug='basketball', default_xp=50)
        self.act_running = ActivityType.objects.create(name='Running', slug='running', default_xp=50)
        
        self.badge_event = Badge.objects.create(name="Bball 26", slug="bball-26", is_active=True)
        
        self.now = timezone.now()
        
        self.event_bball = GravityEvent.objects.create(
            name="Basketball Week",
            slug="bball-week",
            starts_at=self.now - timedelta(days=1),
            ends_at=self.now + timedelta(days=1),
            activity_type=self.act_bball,
            xp_multiplier=2.0,
            flat_xp_bonus=20,
            badge=self.badge_event
        )
        
        self.event_global = GravityEvent.objects.create(
            name="Global Weekend",
            slug="global",
            starts_at=self.now - timedelta(days=1),
            ends_at=self.now + timedelta(days=1),
            activity_type=None,
            xp_multiplier=1.5,
            flat_xp_bonus=10
        )

    def create_participation(self, act_type, joined_at):
        session = ActivitySession.objects.create(activity_type=act_type, created_by=self.user, location=Point(0,0))
        p = Participation.objects.create(session=session, user=self.user, status=Participation.Status.COMPLETED)
        Participation.objects.filter(id=p.id).update(joined_at=joined_at)
        p.refresh_from_db()
        return p

    def test_overlap_event_xp(self):
        # User plays basketball. Both events apply. 
        # Max multiplier is 2.0. Flat is 20 + 10 = 30.
        # Base XP = 50. Total bonus = 50 * (2.0 - 1.0) + 30 = 80.
        p = self.create_participation(self.act_bball, self.now)
        
        rewards = evaluate_events_for_participation(self.user, p, 50)
        
        # 2 events
        self.assertEqual(len(rewards), 2)
        
        # Combined event XP transaction
        xpts = XPTransaction.objects.filter(participation=p, reason=XPTransaction.Reason.EVENT)
        self.assertEqual(xpts.count(), 1)
        self.assertEqual(xpts.first().amount, 80)
        
        # Idempotency checks
        rewards_dup = evaluate_events_for_participation(self.user, p, 50)
        self.assertEqual(len(rewards_dup), 0)

    def test_boundary_times(self):
        # Before starts_at
        p_before = self.create_participation(self.act_bball, self.event_bball.starts_at - timedelta(seconds=1))
        res1 = evaluate_events_for_participation(self.user, p_before, 50)
        self.assertEqual(len(res1), 0)

        # Exactly at starts_at (eligible)
        p_start = self.create_participation(self.act_bball, self.event_bball.starts_at)
        res_start = evaluate_events_for_participation(self.user, p_start, 50)
        self.assertEqual(len(res_start), 2)

        # Exactly at ends_at (NOT eligible, half-open interval)
        p_end = self.create_participation(self.act_bball, self.event_bball.ends_at)
        res_end = evaluate_events_for_participation(self.user2, p_end, 50)
        self.assertEqual(len(res_end), 0)

        # After ends_at
        p_after = self.create_participation(self.act_bball, self.event_bball.ends_at + timedelta(seconds=1))
        res2 = evaluate_events_for_participation(self.user2, p_after, 50)
        self.assertEqual(len(res2), 0)

    def test_activity_matching(self):
        p_run = self.create_participation(self.act_running, self.now)
        rewards = evaluate_events_for_participation(self.user, p_run, 50)
        
        # Running should ONLY match Global Weekend (1)
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0]['event'], 'Global Weekend')
        
        xpts = XPTransaction.objects.filter(participation=p_run, reason=XPTransaction.Reason.EVENT)
        self.assertEqual(xpts.first().amount, 35) # 50 * 0.5 + 10 = 35
        
    def test_dynamic_pickleball_event(self):
        # "Create a new Event through model/admin-compatible flow... Pickleball Weekend"
        act_pb = ActivityType.objects.create(name='Pickleball', slug='pickleball', default_xp=40)
        badge_pb = Badge.objects.create(name='PB Star', slug='pb-star', is_active=True)
        
        ev_pb = GravityEvent.objects.create(
            name="Pickleball Weekend",
            slug="pb-weekend",
            starts_at=self.now - timedelta(hours=1),
            ends_at=self.now + timedelta(hours=5),
            activity_type=act_pb,
            xp_multiplier=1.5,
            flat_xp_bonus=20,
            badge=badge_pb
        )
        
        p = self.create_participation(act_pb, self.now)
        rewards = evaluate_events_for_participation(self.user2, p, 40)
        
        # Matches global and pb
        self.assertEqual(len(rewards), 2)
        # PB badge awarded
        from .models import UserBadge
        self.assertTrue(UserBadge.objects.filter(user=self.user2, badge=badge_pb).exists())
