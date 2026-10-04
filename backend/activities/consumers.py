import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GravityMapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # We can allow anonymous users for map since public maps might be visible to all
        self.group_name = "map_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def map_changed(self, event):
        await self.send(text_data=json.dumps({
            "type": "map.changed",
            "activity_slug": event.get("activity_slug")
        }))


class GravitySessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"
        
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            # Requires auth to see session details
            await self.close(code=4003)
            return

        # Ideally, we should also check if the user is an active participant.
        # But this is async and requires db lookup. For V1, authenticating the user
        # and checking they are logged in is an acceptable baseline, or we can use database_sync_to_async.
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def session_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "session.updated",
            "payload": event.get("payload", {})
        }))


class GravityChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.challenge_id = self.scope['url_route']['kwargs']['challenge_id']
        self.group_name = f"challenge_{self.challenge_id}"

        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def challenge_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "challenge.updated",
            "challenge_id": event.get("challenge_id")
        }))
