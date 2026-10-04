from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from accounts.models import User, Friendship
from activities.models import (
    ActivityType,
    ActivityMetric,
    FriendChallenge,
    ChallengeParticipant,
    ChallengeReward,
    Participation,
    MetricValue,
    XPTransaction,
)
from activities.logic.xp_service import award_xp

DEFAULT_CHALLENGE_PARTICIPATION_XP = getattr(settings, 'GRAVITY_CHALLENGE_PARTICIPATION_XP', 25)
DEFAULT_CHALLENGE_WIN_XP = getattr(settings, 'GRAVITY_CHALLENGE_WIN_XP', 50)


def notify_challenge_updated(challenge_id: int):
    """
    Emits a realtime WebSocket message to all participants of this challenge.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"challenge_{challenge_id}",
                {
                    "type": "challenge_updated",
                    "challenge_id": challenge_id
                }
            )
    except Exception:
        pass


def validate_challenge_creation(
    creator: User,
    activity_type: ActivityType,
    metric: ActivityMetric,
    challenge_type: str,
    target_value: float,
    starts_at: datetime,
    ends_at: datetime,
    invitee_ids: list
):
    """
    Validates all domain constraints for creating a FriendChallenge.
    """
    if not creator or not creator.is_authenticated:
        raise PermissionDenied("Authentication required to create a challenge.")

    if starts_at >= ends_at:
        raise ValidationError("starts_at must be strictly before ends_at.")

    if metric.activity_type_id != activity_type.id:
        raise ValidationError("Selected metric does not belong to the chosen activity type.")

    if challenge_type not in FriendChallenge.ChallengeType.values:
        raise ValidationError(f"Invalid challenge type: {challenge_type}")

    # Target requirements
    if challenge_type in [FriendChallenge.ChallengeType.FIRST_TO_TARGET, FriendChallenge.ChallengeType.COOPERATIVE_TARGET]:
        if target_value is None or float(target_value) <= 0:
            raise ValidationError("target_value must be greater than 0 for this challenge type.")

    # Aggregation suitability
    if metric.aggregation in [ActivityMetric.AggregationMode.MAX, ActivityMetric.AggregationMode.AVERAGE]:
        if challenge_type in [FriendChallenge.ChallengeType.FIRST_TO_TARGET, FriendChallenge.ChallengeType.COOPERATIVE_TARGET]:
            raise ValidationError("Cumulative challenges require an additive metric.")

    # Invitees validation
    if not invitee_ids:
        raise ValidationError("At least one friend must be invited to the challenge.")

    clean_invitees = []
    for inv_id in invitee_ids:
        try:
            target_id = int(inv_id)
        except (ValueError, TypeError):
            continue

        if target_id == creator.id:
            raise ValidationError("You cannot invite yourself as a friend participant.")

        try:
            friend_user = User.objects.get(id=target_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError(f"User {target_id} does not exist.")

        # STRICT FRIENDS-ONLY RULE: Must be an accepted mutual friend
        if not Friendship.are_friends(creator, friend_user):
            raise ValidationError(f"User @{friend_user.username} is not an accepted friend. Challenges are friends-only.")

        clean_invitees.append(friend_user)

    if not clean_invitees:
        raise ValidationError("No valid accepted friends found in invitees list.")

    return clean_invitees


@transaction.atomic
def create_challenge(
    creator: User,
    activity_type: ActivityType,
    metric: ActivityMetric,
    challenge_type: str,
    target_value: float,
    starts_at: datetime,
    ends_at: datetime,
    invitee_ids: list,
    title: str = None
) -> FriendChallenge:
    """
    Creates a new FriendChallenge and registers participants.
    """
    clean_invitees = validate_challenge_creation(
        creator=creator,
        activity_type=activity_type,
        metric=metric,
        challenge_type=challenge_type,
        target_value=target_value,
        starts_at=starts_at,
        ends_at=ends_at,
        invitee_ids=invitee_ids
    )

    now = timezone.now()
    initial_status = FriendChallenge.Status.PENDING

    challenge = FriendChallenge.objects.create(
        title=title.strip() if title else f"{activity_type.name} {challenge_type.replace('_', ' ').title()}",
        created_by=creator,
        activity_type=activity_type,
        metric=metric,
        challenge_type=challenge_type,
        target_value=float(target_value) if target_value is not None else None,
        starts_at=starts_at,
        ends_at=ends_at,
        status=initial_status
    )

    # Creator is automatically an accepted participant
    ChallengeParticipant.objects.create(
        challenge=challenge,
        user=creator,
        invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED,
        joined_at=now
    )

    # Register invitees
    for friend in clean_invitees:
        ChallengeParticipant.objects.create(
            challenge=challenge,
            user=friend,
            invitation_status=ChallengeParticipant.InvitationStatus.INVITED
        )

    notify_challenge_updated(challenge.id)
    return challenge


@transaction.atomic
def accept_challenge_invitation(user: User, challenge_id: int) -> FriendChallenge:
    """
    Accepts an incoming challenge invitation.
    """
    try:
        challenge = FriendChallenge.objects.select_for_update().get(id=challenge_id)
    except FriendChallenge.DoesNotExist:
        raise ValidationError("Challenge not found.")

    if challenge.status in [FriendChallenge.Status.COMPLETED, FriendChallenge.Status.CANCELLED, FriendChallenge.Status.EXPIRED]:
        raise ValidationError("Challenge is no longer accepting participants.")

    try:
        participant = ChallengeParticipant.objects.select_for_update().get(challenge=challenge, user=user)
    except ChallengeParticipant.DoesNotExist:
        raise ValidationError("You were not invited to this challenge.")

    if participant.invitation_status == ChallengeParticipant.InvitationStatus.ACCEPTED:
        return challenge

    now = timezone.now()
    participant.invitation_status = ChallengeParticipant.InvitationStatus.ACCEPTED
    participant.joined_at = now
    participant.save(update_fields=['invitation_status', 'joined_at', 'updated_at'])

    # Activate challenge if time window is open
    if challenge.status == FriendChallenge.Status.PENDING:
        if challenge.starts_at <= now < challenge.ends_at:
            challenge.status = FriendChallenge.Status.ACTIVE
            challenge.save(update_fields=['status', 'updated_at'])

    notify_challenge_updated(challenge.id)
    return challenge


@transaction.atomic
def decline_challenge_invitation(user: User, challenge_id: int) -> FriendChallenge:
    """
    Declines an incoming challenge invitation.
    If all invitees decline, auto-cancels the challenge.
    """
    try:
        challenge = FriendChallenge.objects.select_for_update().get(id=challenge_id)
    except FriendChallenge.DoesNotExist:
        raise ValidationError("Challenge not found.")

    try:
        participant = ChallengeParticipant.objects.select_for_update().get(challenge=challenge, user=user)
    except ChallengeParticipant.DoesNotExist:
        raise ValidationError("You are not a participant in this challenge.")

    participant.invitation_status = ChallengeParticipant.InvitationStatus.DECLINED
    participant.save(update_fields=['invitation_status', 'updated_at'])

    # Check remaining participants
    has_other_accepted = challenge.participants.filter(
        invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED
    ).exclude(user=challenge.created_by).exists()

    has_pending_invites = challenge.participants.filter(
        invitation_status=ChallengeParticipant.InvitationStatus.INVITED
    ).exists()

    if not has_other_accepted and not has_pending_invites:
        # All friends declined -> auto-cancel
        challenge.status = FriendChallenge.Status.CANCELLED
        challenge.save(update_fields=['status', 'updated_at'])

    notify_challenge_updated(challenge.id)
    return challenge


@transaction.atomic
def cancel_challenge(user: User, challenge_id: int) -> FriendChallenge:
    """
    Creator cancels a challenge.
    """
    try:
        challenge = FriendChallenge.objects.select_for_update().get(id=challenge_id)
    except FriendChallenge.DoesNotExist:
        raise ValidationError("Challenge not found.")

    if challenge.created_by_id != user.id:
        raise PermissionDenied("Only the challenge creator can cancel this challenge.")

    if challenge.status in [FriendChallenge.Status.COMPLETED, FriendChallenge.Status.CANCELLED]:
        raise ValidationError("Cannot cancel a challenge that is already finished.")

    challenge.status = FriendChallenge.Status.CANCELLED
    challenge.save(update_fields=['status', 'updated_at'])

    notify_challenge_updated(challenge.id)
    return challenge


@transaction.atomic
def distribute_challenge_rewards(challenge: FriendChallenge):
    """
    Idempotently distributes XP rewards for a completed challenge.
    Enforces that rewards cannot be duplicated on retries or recalculations.
    """
    if challenge.status != FriendChallenge.Status.COMPLETED:
        return

    participants = list(challenge.participants.filter(
        invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED
    ).select_related('user'))

    if challenge.challenge_type == FriendChallenge.ChallengeType.FIRST_TO_TARGET:
        # Winner reward
        if challenge.winner:
            reward, created = ChallengeReward.objects.get_or_create(
                challenge=challenge,
                user=challenge.winner,
                reward_type=ChallengeReward.RewardType.WINNER,
                defaults={'amount': DEFAULT_CHALLENGE_WIN_XP}
            )
            if created:
                xpt = award_xp(
                    user=challenge.winner,
                    amount=DEFAULT_CHALLENGE_WIN_XP,
                    reason=XPTransaction.Reason.CHALLENGE,
                    description=f"Won Challenge: {challenge.title}",
                    activity_type=challenge.activity_type
                )
                reward.xp_transaction = xpt
                reward.save(update_fields=['xp_transaction'])

        # Completion reward for all who contributed
        for p in participants:
            if p.progress > 0:
                reward, created = ChallengeReward.objects.get_or_create(
                    challenge=challenge,
                    user=p.user,
                    reward_type=ChallengeReward.RewardType.COMPLETION,
                    defaults={'amount': DEFAULT_CHALLENGE_PARTICIPATION_XP}
                )
                if created:
                    xpt = award_xp(
                        user=p.user,
                        amount=DEFAULT_CHALLENGE_PARTICIPATION_XP,
                        reason=XPTransaction.Reason.CHALLENGE,
                        description=f"Completed Challenge: {challenge.title}",
                        activity_type=challenge.activity_type
                    )
                    reward.xp_transaction = xpt
                    reward.save(update_fields=['xp_transaction'])

    elif challenge.challenge_type == FriendChallenge.ChallengeType.HIGHEST_BY_DEADLINE:
        # All co-winners (rank 1) get Winner XP
        for p in participants:
            if p.is_winner or p.rank == 1:
                reward, created = ChallengeReward.objects.get_or_create(
                    challenge=challenge,
                    user=p.user,
                    reward_type=ChallengeReward.RewardType.WINNER,
                    defaults={'amount': DEFAULT_CHALLENGE_WIN_XP}
                )
                if created:
                    xpt = award_xp(
                        user=p.user,
                        amount=DEFAULT_CHALLENGE_WIN_XP,
                        reason=XPTransaction.Reason.CHALLENGE,
                        description=f"Won Challenge: {challenge.title}",
                        activity_type=challenge.activity_type
                    )
                    reward.xp_transaction = xpt
                    reward.save(update_fields=['xp_transaction'])

            # Completion reward for participants with progress
            if p.progress > 0:
                reward, created = ChallengeReward.objects.get_or_create(
                    challenge=challenge,
                    user=p.user,
                    reward_type=ChallengeReward.RewardType.COMPLETION,
                    defaults={'amount': DEFAULT_CHALLENGE_PARTICIPATION_XP}
                )
                if created:
                    xpt = award_xp(
                        user=p.user,
                        amount=DEFAULT_CHALLENGE_PARTICIPATION_XP,
                        reason=XPTransaction.Reason.CHALLENGE,
                        description=f"Completed Challenge: {challenge.title}",
                        activity_type=challenge.activity_type
                    )
                    reward.xp_transaction = xpt
                    reward.save(update_fields=['xp_transaction'])

    elif challenge.challenge_type == FriendChallenge.ChallengeType.COOPERATIVE_TARGET:
        # Cooperative completion reward for all contributing participants
        for p in participants:
            if p.progress > 0:
                reward, created = ChallengeReward.objects.get_or_create(
                    challenge=challenge,
                    user=p.user,
                    reward_type=ChallengeReward.RewardType.COMPLETION,
                    defaults={'amount': DEFAULT_CHALLENGE_PARTICIPATION_XP}
                )
                if created:
                    xpt = award_xp(
                        user=p.user,
                        amount=DEFAULT_CHALLENGE_PARTICIPATION_XP,
                        reason=XPTransaction.Reason.CHALLENGE,
                        description=f"Completed Cooperative Goal: {challenge.title}",
                        activity_type=challenge.activity_type
                    )
                    reward.xp_transaction = xpt
                    reward.save(update_fields=['xp_transaction'])


@transaction.atomic
def calculate_and_update_challenge_progress(challenge: FriendChallenge, now: datetime = None) -> FriendChallenge:
    """
    Computes challenge progress, evaluates completion/winners, and awards XP.
    """
    if now is None:
        now = timezone.now()

    # If already concluded, do not re-evaluate winners or status
    if challenge.status in [FriendChallenge.Status.CANCELLED, FriendChallenge.Status.EXPIRED]:
        return challenge

    # 1. State Transitions based on time & acceptance
    accepted_invitees = challenge.participants.filter(
        invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED
    ).exclude(user=challenge.created_by)

    if challenge.status == FriendChallenge.Status.PENDING:
        if now >= challenge.starts_at:
            if accepted_invitees.exists():
                challenge.status = FriendChallenge.Status.ACTIVE
            elif now >= challenge.ends_at:
                challenge.status = FriendChallenge.Status.EXPIRED
                challenge.save(update_fields=['status', 'updated_at'])
                return challenge

    if challenge.status == FriendChallenge.Status.ACTIVE:
        if now >= challenge.ends_at and challenge.challenge_type != FriendChallenge.ChallengeType.HIGHEST_BY_DEADLINE:
            # First-to-target or cooperative deadline reached without prior completion
            pass # We will check progress below; if still unmet, marks EXPIRED

    # 2. Compute progress for each accepted participant
    accepted_participants = list(challenge.participants.filter(
        invitation_status=ChallengeParticipant.InvitationStatus.ACCEPTED
    ).select_related('user'))

    for p in accepted_participants:
        # Only COMPLETED / non-active participations qualify (V1 integrity rule)
        qualifying_parts = Participation.objects.filter(
            user=p.user,
            session__activity_type=challenge.activity_type,
            joined_at__gte=challenge.starts_at,
            joined_at__lt=challenge.ends_at,
            status__in=[Participation.Status.COMPLETED, Participation.Status.LEFT, Participation.Status.AUTO_STOPPED]
        ).exclude(status=Participation.Status.ACTIVE)

        mvs = MetricValue.objects.filter(
            participation__in=qualifying_parts,
            metric=challenge.metric
        )
        total_metric = sum(float(mv.value) for mv in mvs)
        p.progress = round(total_metric, 2)
        p.save(update_fields=['progress', 'updated_at'])

    # 3. Evaluate Challenge Types
    if challenge.status in [FriendChallenge.Status.ACTIVE, FriendChallenge.Status.PENDING]:
        if challenge.challenge_type == FriendChallenge.ChallengeType.FIRST_TO_TARGET:
            qualifying_winners = [p for p in accepted_participants if p.progress >= challenge.target_value]
            if qualifying_winners:
                # Determine who crossed the target first using chronological participation left_at
                winner_p = None
                earliest_time = None

                for p in qualifying_winners:
                    parts = Participation.objects.filter(
                        user=p.user,
                        session__activity_type=challenge.activity_type,
                        joined_at__gte=challenge.starts_at,
                        joined_at__lt=challenge.ends_at,
                        status__in=[Participation.Status.COMPLETED, Participation.Status.LEFT, Participation.Status.AUTO_STOPPED]
                    ).order_by('joined_at')

                    cum = 0.0
                    for part in parts:
                        mv = MetricValue.objects.filter(participation=part, metric=challenge.metric).first()
                        if mv:
                            cum += float(mv.value)
                            if cum >= challenge.target_value:
                                finish_time = part.left_at or part.joined_at
                                if earliest_time is None or finish_time < earliest_time:
                                    earliest_time = finish_time
                                    winner_p = p
                                break

                if winner_p:
                    challenge.winner = winner_p.user
                    challenge.status = FriendChallenge.Status.COMPLETED
                    challenge.completed_at = earliest_time or now
                    challenge.save(update_fields=['winner', 'status', 'completed_at', 'updated_at'])

                    winner_p.is_winner = True
                    winner_p.rank = 1
                    winner_p.save(update_fields=['is_winner', 'rank', 'updated_at'])

                    # Rank other participants
                    other_parts = sorted([p for p in accepted_participants if p.id != winner_p.id], key=lambda x: -x.progress)
                    for idx, op in enumerate(other_parts, start=2):
                        op.rank = idx
                        op.is_winner = False
                        op.save(update_fields=['rank', 'is_winner', 'updated_at'])

                    distribute_challenge_rewards(challenge)
                    notify_challenge_updated(challenge.id)
                    return challenge

            # If deadline passed and target not met
            if now >= challenge.ends_at:
                challenge.status = FriendChallenge.Status.EXPIRED
                challenge.save(update_fields=['status', 'updated_at'])
                notify_challenge_updated(challenge.id)
                return challenge

        elif challenge.challenge_type == FriendChallenge.ChallengeType.HIGHEST_BY_DEADLINE:
            # During the challenge window: rank live for display
            sorted_parts = sorted(accepted_participants, key=lambda p: -p.progress)
            current_rank = 1
            for idx, p in enumerate(sorted_parts):
                if idx > 0 and p.progress < sorted_parts[idx - 1].progress:
                    current_rank = idx + 1
                p.rank = current_rank
                p.is_winner = (current_rank == 1 and p.progress > 0)
                p.save(update_fields=['rank', 'is_winner', 'updated_at'])

            # Finalize when deadline passes
            if now >= challenge.ends_at:
                challenge.status = FriendChallenge.Status.COMPLETED
                challenge.completed_at = challenge.ends_at
                co_winners = [p for p in sorted_parts if p.rank == 1 and p.progress > 0]
                if len(co_winners) == 1:
                    challenge.winner = co_winners[0].user
                else:
                    challenge.winner = None # Co-winners
                challenge.save(update_fields=['status', 'completed_at', 'winner', 'updated_at'])

                distribute_challenge_rewards(challenge)
                notify_challenge_updated(challenge.id)
                return challenge

        elif challenge.challenge_type == FriendChallenge.ChallengeType.COOPERATIVE_TARGET:
            combined = sum(p.progress for p in accepted_participants)
            if combined >= challenge.target_value:
                challenge.status = FriendChallenge.Status.COMPLETED
                challenge.completed_at = now
                challenge.save(update_fields=['status', 'completed_at', 'updated_at'])

                distribute_challenge_rewards(challenge)
                notify_challenge_updated(challenge.id)
                return challenge

            # If deadline passed and combined target not reached
            if now >= challenge.ends_at:
                challenge.status = FriendChallenge.Status.EXPIRED
                challenge.save(update_fields=['status', 'updated_at'])
                notify_challenge_updated(challenge.id)
                return challenge

    challenge.save(update_fields=['status', 'updated_at'])
    return challenge
