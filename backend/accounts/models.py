from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class PrivacyMode(models.TextChoices):
        HIDDEN = 'hidden', _('Hidden')
        BLURRED = 'blurred', _('Blurred / Approximate')
        FRIENDS = 'friends', _('Friends Only')
        EXACT = 'exact', _('Exact Location')

    display_name = models.CharField(max_length=255, blank=True)
    total_xp = models.PositiveIntegerField(default=0)
    current_level = models.PositiveIntegerField(default=1)
    location_privacy_mode = models.CharField(
        max_length=20,
        choices=PrivacyMode.choices,
        default=PrivacyMode.BLURRED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.username


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        ACCEPTED = 'accepted', _('Accepted')
        DECLINED = 'declined', _('Declined')
        BLOCKED = 'blocked', _('Blocked')

    user_a = models.ForeignKey(
        User,
        related_name='friendships_as_a',
        on_delete=models.CASCADE
    )
    user_b = models.ForeignKey(
        User,
        related_name='friendships_as_b',
        on_delete=models.CASCADE
    )
    initiated_by = models.ForeignKey(
        User,
        related_name='friendships_initiated',
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_a', 'user_b'],
                name='unique_canonical_friendship_pair'
            ),
            models.CheckConstraint(
                check=models.Q(user_a__lt=models.F('user_b')),
                name='friendship_user_a_less_than_user_b'
            ),
        ]
        indexes = [
            models.Index(fields=['user_a', 'status']),
            models.Index(fields=['user_b', 'status']),
            models.Index(fields=['initiated_by', 'status']),
        ]

    def __str__(self):
        return f"{self.user_a.username} <-> {self.user_b.username} ({self.status})"

    @classmethod
    def get_canonical_pair(cls, u1, u2):
        if u1.id == u2.id:
            raise ValueError("A user cannot friend themselves.")
        return (u1, u2) if u1.id < u2.id else (u2, u1)

    @classmethod
    def are_friends(cls, u1, u2):
        if not u1 or not u2 or not u1.is_authenticated or not u2.is_authenticated or u1.id == u2.id:
            return False
        user_low, user_high = cls.get_canonical_pair(u1, u2)
        return cls.objects.filter(user_a=user_low, user_b=user_high, status=cls.Status.ACCEPTED).exists()

