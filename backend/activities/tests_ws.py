from django.test import TransactionTestCase
from channels.testing import WebsocketCommunicator
from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter
from django.contrib.auth import get_user_model
from activities.consumers import GravityMapConsumer, GravitySessionConsumer
from asgiref.sync import async_to_sync
import uuid

User = get_user_model()

class WebSocketTests(TransactionTestCase):
    def test_map_consumer_connect(self):
        from activities.routing import websocket_urlpatterns
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        
        async def run_test():
            communicator = WebsocketCommunicator(application, "/ws/gravity/")
            connected, subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()
            
        async_to_sync(run_test)()

    def test_session_consumer_requires_auth(self):
        from activities.routing import websocket_urlpatterns
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        
        async def run_test():
            session_id = str(uuid.uuid4())
            communicator = WebsocketCommunicator(application, f"/ws/gravity/session/{session_id}/")
            connected, subprotocol = await communicator.connect()
            self.assertFalse(connected)
            
        async_to_sync(run_test)()
