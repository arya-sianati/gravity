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

urlpatterns = [
    path('pulse/now/', PulseNowAPIView.as_view(), name='pulse-now'),
    path('map/live/', LiveMapAPIView.as_view(), name='map-live'),
    path('join/<uuid:token>/', JoinTokenAPIView.as_view(), name='join-token'),
    path('activity-types/', ActivityTypeListAPIView.as_view(), name='activity-type-list'),
    path('activity-types/<slug:slug>/', ActivityTypeDetailAPIView.as_view(), name='activity-type-detail'),
    path('leaderboards/<slug:activity_slug>/', LeaderboardAPIView.as_view(), name='leaderboard'),
    path('me/active-participation/', ActiveParticipationAPIView.as_view(), name='active-participation'),
    path('participations/<int:pk>/metrics/', ParticipationMetricsAPIView.as_view(), name='participation-metrics'),
    path('', include(router.urls)),
]
