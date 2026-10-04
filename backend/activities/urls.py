from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityTypeListAPIView, 
    ActivityTypeDetailAPIView,
    ActivitySessionViewSet,
    ActiveParticipationAPIView,
    LiveMapAPIView,
    JoinTokenAPIView,
    ParticipationMetricsAPIView,
    LeaderboardAPIView,
    PulseNowAPIView
)

router = DefaultRouter()
router.register(r'sessions', ActivitySessionViewSet, basename='session')

from .views import GravityEventViewSet, SeasonViewSet
router.register(r'events', GravityEventViewSet, basename='event')
router.register(r'seasons', SeasonViewSet, basename='season')

from .views import (
    FriendChallengeListCreateAPIView,
    FriendChallengeDetailAPIView,
    FriendChallengeAcceptAPIView,
    FriendChallengeDeclineAPIView,
    FriendChallengeCancelAPIView,
    ActivityLocationHeartbeatAPIView,
    ParticipationHeartbeatAPIView,
)

urlpatterns = [
    path('pulse/now/', PulseNowAPIView.as_view(), name='pulse-now'),
    path('map/live/', LiveMapAPIView.as_view(), name='map-live'),
    path('join/<uuid:token>/', JoinTokenAPIView.as_view(), name='join-token'),
    path('activity-types/', ActivityTypeListAPIView.as_view(), name='activity-type-list'),
    path('activity-types/<slug:slug>/', ActivityTypeDetailAPIView.as_view(), name='activity-type-detail'),
    path('leaderboards/<slug:activity_slug>/', LeaderboardAPIView.as_view(), name='leaderboard'),
    path('me/active-participation/', ActiveParticipationAPIView.as_view(), name='active-participation'),
    path('participations/<int:pk>/metrics/', ParticipationMetricsAPIView.as_view(), name='participation-metrics'),

    # Phase 17: Friend Challenges
    path('challenges/', FriendChallengeListCreateAPIView.as_view(), name='challenge-list-create'),
    path('challenges/<int:pk>/', FriendChallengeDetailAPIView.as_view(), name='challenge-detail'),
    path('challenges/<int:pk>/accept/', FriendChallengeAcceptAPIView.as_view(), name='challenge-accept'),
    path('challenges/<int:pk>/decline/', FriendChallengeDeclineAPIView.as_view(), name='challenge-decline'),
    path('challenges/<int:pk>/cancel/', FriendChallengeCancelAPIView.as_view(), name='challenge-cancel'),

    # Phase 18: Auto-Stop & Location Heartbeat
    path('me/activity-location/', ActivityLocationHeartbeatAPIView.as_view(), name='activity-location-heartbeat'),
    path('participations/<int:pk>/heartbeat/', ParticipationHeartbeatAPIView.as_view(), name='participation-heartbeat'),

    path('', include(router.urls)),
]
