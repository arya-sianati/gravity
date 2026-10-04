from django.urls import path
from .views import ActivityTypeListAPIView, ActivityTypeDetailAPIView

urlpatterns = [
    path('activity-types/', ActivityTypeListAPIView.as_view(), name='activity-type-list'),
    path('activity-types/<slug:slug>/', ActivityTypeDetailAPIView.as_view(), name='activity-type-detail'),
]
