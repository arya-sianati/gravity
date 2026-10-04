from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import ActivityType
from .serializers import ActivityTypeSerializer

class ActivityTypeListAPIView(generics.ListAPIView):
    serializer_class = ActivityTypeSerializer
    permission_classes = [AllowAny]
    queryset = ActivityType.objects.filter(is_active=True).prefetch_related('metrics')

class ActivityTypeDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ActivityTypeSerializer
    permission_classes = [AllowAny]
    queryset = ActivityType.objects.filter(is_active=True).prefetch_related('metrics')
    lookup_field = 'slug'
