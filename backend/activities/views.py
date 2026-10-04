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

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.db import transaction
from django.utils import timezone
from .models import ActivitySession, Participation, ActivityType
from .serializers import (
    ActivitySessionSerializer,
    ActivitySessionCreateSerializer,
    NearbySessionSerializer,
    ParticipationSerializer
)

class ActivitySessionViewSet(viewsets.ModelViewSet):
    queryset = ActivitySession.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ActivitySessionCreateSerializer
        return ActivitySessionSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 1. Enforce rule: max one active participation per user
        if Participation.objects.filter(user=request.user, status=Participation.Status.ACTIVE).exists():
            return Response(
                {"detail": "You are already active in another session."},
                status=status.HTTP_409_CONFLICT
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity_type = serializer.validated_data['activity_type']
        if not activity_type.is_active:
            return Response({"detail": "This activity type is disabled."}, status=status.HTTP_400_BAD_REQUEST)

        # Build location point
        lat = serializer.validated_data.pop('lat')
        lng = serializer.validated_data.pop('lng')
        location = Point(lng, lat, srid=4326)

        session = ActivitySession.objects.create(
            created_by=request.user,
            location=location,
            **serializer.validated_data
        )

        # Create participation
        Participation.objects.create(
            session=session,
            user=request.user,
            status=Participation.Status.ACTIVE,
            join_method=Participation.JoinMethod.SELF
        )

        resp_serializer = ActivitySessionSerializer(session)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def join(self, request, pk=None):
        session = self.get_object()

        if session.status != ActivitySession.Status.ACTIVE:
            return Response({"detail": "Session is not active."}, status=status.HTTP_400_BAD_REQUEST)

        if not session.activity_type.is_active:
            return Response({"detail": "This activity type is disabled."}, status=status.HTTP_400_BAD_REQUEST)

        if Participation.objects.filter(session=session, user=request.user, status=Participation.Status.ACTIVE).exists():
            return Response({"detail": "You are already active in this session."}, status=status.HTTP_409_CONFLICT)

        if Participation.objects.filter(user=request.user, status=Participation.Status.ACTIVE).exists():
            return Response({"detail": "You are already active in another session."}, status=status.HTTP_409_CONFLICT)

        Participation.objects.create(
            session=session,
            user=request.user,
            status=Participation.Status.ACTIVE,
            join_method=Participation.JoinMethod.SELF
        )

        return Response(ActivitySessionSerializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def leave(self, request, pk=None):
        session = self.get_object()

        try:
            participation = Participation.objects.get(
                session=session,
                user=request.user,
                status=Participation.Status.ACTIVE
            )
        except Participation.DoesNotExist:
            return Response({"detail": "You are not active in this session."}, status=status.HTTP_400_BAD_REQUEST)

        participation.status = Participation.Status.LEFT
        participation.left_at = timezone.now()
        participation.save()

        active_count = session.participations.filter(status=Participation.Status.ACTIVE).count()
        if active_count == 0 and session.status == ActivitySession.Status.ACTIVE:
            session.status = ActivitySession.Status.ENDED
            session.ended_at = timezone.now()
            session.save()

        return Response({"detail": "Successfully left the session."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        activity_slug = request.query_params.get('activity')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        if not all([activity_slug, lat, lng]):
            return Response({"detail": "Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lng = float(lng)
            point = Point(lng, lat, srid=4326)
        except ValueError:
            return Response({"detail": "Invalid coordinates."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            activity = ActivityType.objects.get(slug=activity_slug, is_active=True)
        except ActivityType.DoesNotExist:
            return Response({"detail": "Activity type not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

        radius_m = activity.join_suggestion_radius_m

        sessions = ActivitySession.objects.filter(
            activity_type=activity,
            status=ActivitySession.Status.ACTIVE,
            location__distance_lte=(point, D(m=radius_m))
        ).annotate(
            distance=Distance('location', point)
        ).order_by('distance')

        return Response(NearbySessionSerializer(sessions, many=True).data, status=status.HTTP_200_OK)

class ActiveParticipationAPIView(generics.RetrieveAPIView):
    serializer_class = ActivitySessionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            participation = Participation.objects.get(user=self.request.user, status=Participation.Status.ACTIVE)
            return participation.session
        except Participation.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response(None, status=status.HTTP_200_OK)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

from django.contrib.gis.geos import Polygon
from rest_framework.views import APIView
from django.db.models import Count, Q
from .services import get_privacy_safe_feature

class LiveMapAPIView(APIView):
    permission_classes = []
    
    def get(self, request):
        bbox_str = request.query_params.get('bbox')
        if not bbox_str:
            return Response({"detail": "Missing bbox parameter."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            west, south, east, north = map(float, bbox_str.split(','))
        except ValueError:
            return Response({"detail": "Malformed bbox parameter."}, status=status.HTTP_400_BAD_REQUEST)
            
        if west >= east or south >= north:
            return Response({"detail": "Invalid bbox coordinate ordering."}, status=status.HTTP_400_BAD_REQUEST)
            
        bbox_polygon = Polygon.from_bbox((west, south, east, north))
        
        # Query active sessions within bbox
        sessions = ActivitySession.objects.filter(
            status=ActivitySession.Status.ACTIVE,
            location__within=bbox_polygon
        ).select_related('created_by', 'activity_type').annotate(
            active_count=Count('participations', filter=Q(participations__status=Participation.Status.ACTIVE))
        )
        
        features = []
        user = request.user if request.user.is_authenticated else None
        
        for session in sessions:
            if session.active_count == 0:
                continue # Safety skip
            feat = get_privacy_safe_feature(session, request_user=user)
            if feat:
                features.append(feat)
                
        return Response({
            "type": "FeatureCollection",
            "features": features
        }, status=status.HTTP_200_OK)

