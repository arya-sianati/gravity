from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityTypeListAPIView, 
    ActivityTypeDetailAPIView,
    ActivitySessionViewSet,
    ActiveParticipationAPIView,
    LiveMapAPIView,
    JoinTokenAPIView
)

router = DefaultRouter()
router.register(r'sessions', ActivitySessionViewSet, basename='session')

urlpatterns = [
    path('map/live/', LiveMapAPIView.as_view(), name='map-live'),
    path('join/<uuid:token>/', JoinTokenAPIView.as_view(), name='join-token'),
    path('activity-types/', ActivityTypeListAPIView.as_view(), name='activity-type-list'),
    path('activity-types/<slug:slug>/', ActivityTypeDetailAPIView.as_view(), name='activity-type-detail'),
    path('me/active-participation/', ActiveParticipationAPIView.as_view(), name='active-participation'),
    path('', include(router.urls)),
]
