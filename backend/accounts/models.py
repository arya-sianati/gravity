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
