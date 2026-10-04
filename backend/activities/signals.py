from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ActivitySession, Participation, ActivityType

def broadcast_map_change(activity_slug):
    channel_layer = get_channel_layer()
    if channel_layer and activity_slug:
        async_to_sync(channel_layer.group_send)(
            "map_updates",
            {
                "type": "map_changed",
                "activity_slug": activity_slug
            }
        )

def broadcast_session_update(session_id):
    try:
        session = ActivitySession.objects.get(id=session_id)
        active_count = session.participations.filter(status=Participation.Status.ACTIVE).count()
        payload = {
            "session_id": str(session.id),
            "status": session.status,
            "participant_count": active_count
        }
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"session_{session.id}",
                {
                    "type": "session_updated",
                    "payload": payload
                }
            )
    except ActivitySession.DoesNotExist:
        pass


@receiver(post_save, sender=ActivitySession)
def on_session_save(sender, instance, created, **kwargs):
    session_id = instance.id
    try:
        activity_slug = instance.activity_type.slug
    except Exception:
        activity_slug = None

    def _broadcast():
        if activity_slug:
            broadcast_map_change(activity_slug)
        if session_id:
            broadcast_session_update(session_id)
    transaction.on_commit(_broadcast)

@receiver(post_save, sender=Participation)
def on_participation_save(sender, instance, created, **kwargs):
    session_id = instance.session_id
    try:
        activity_slug = instance.session.activity_type.slug
    except Exception:
        activity_slug = None

    def _broadcast():
        if activity_slug:
            broadcast_map_change(activity_slug)
        if session_id:
            broadcast_session_update(session_id)
    transaction.on_commit(_broadcast)

@receiver(post_delete, sender=Participation)
def on_participation_delete(sender, instance, **kwargs):
    session_id = instance.session_id
    try:
        activity_slug = instance.session.activity_type.slug
    except Exception:
        activity_slug = None

    def _broadcast():
        if activity_slug:
            broadcast_map_change(activity_slug)
        if session_id:
            broadcast_session_update(session_id)
    transaction.on_commit(_broadcast)
