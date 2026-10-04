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

    @action(detail=True, methods=['get'])
    def join_code(self, request, pk=None):
        session = self.get_object()
        
        # Must be an active participant
        if not Participation.objects.filter(session=session, user=request.user, status=Participation.Status.ACTIVE).exists():
            return Response({"detail": "You must be an active participant to get the join code."}, status=status.HTTP_403_FORBIDDEN)
            
        if session.status != ActivitySession.Status.ACTIVE:
            return Response({"detail": "Session is no longer active."}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.conf import settings
        base_url = getattr(settings, 'PUBLIC_BASE_URL', 'http://localhost:5173')
        join_url = f"{base_url.rstrip('/')}/join/{session.join_token}"
        
        return Response({
            "join_url": join_url,
            "expires_at": None
        })

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

        source = request.data.get('source') if isinstance(request.data, dict) else None
        if not source:
            source = request.query_params.get('source')

        if source == 'pulse':
            join_method = Participation.JoinMethod.SUGGESTION
        elif source == 'map':
            join_method = Participation.JoinMethod.MAP
        else:
            join_method = Participation.JoinMethod.SELF

        Participation.objects.create(
            session=session,
            user=request.user,
            status=Participation.Status.ACTIVE,
            join_method=join_method
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
        
        # Auto-calculate duration metrics
        duration_seconds = (participation.left_at - participation.joined_at).total_seconds()
        from .models import MetricValue, ActivityMetric
        duration_metrics = session.activity_type.metrics.filter(data_type=ActivityMetric.DataType.DURATION)
        for metric in duration_metrics:
            # If the user hasn't explicitly entered a duration, or we prefer to override with exact:
            # The spec says: "derive/finalize duration from: left_at - joined_at"
            # We'll map duration to whatever the unit is, but let's assume 'minutes' or 'seconds'.
            # Usually duration in DB can be mapped to seconds or minutes. We will store it as seconds,
            # or if the unit says 'minutes', we store it in minutes.
            val = duration_seconds
            if metric.unit and 'min' in metric.unit.lower():
                val = duration_seconds / 60.0
            elif metric.unit and 'hour' in metric.unit.lower():
                val = duration_seconds / 3600.0
            
            MetricValue.objects.update_or_create(
                participation=participation,
                metric=metric,
                defaults={'value': val}
            )

        participation.save()

        # Phase 11: Award XP
        min_duration = getattr(settings, 'GRAVITY_MIN_XP_DURATION_SECONDS', 60)
        from .logic.xp_service import award_xp
        from .logic.streak_service import evaluate_streak
        from .logic.achievement_service import evaluate_after_participation
        
        xp_awarded = None
        level_up = False
        streak_state = None
        badges_earned = []
        
        if duration_seconds >= min_duration:
            old_level = request.user.current_level
            xpt = award_xp(
                user=request.user,
                amount=session.activity_type.default_xp,
                reason='participation',
                description=f"Completed {session.activity_type.name} participation",
                participation=participation,
                activity_type=session.activity_type
            )
            
            # Phase 12: Evaluate streak
            streak, incremented, _ = evaluate_streak(request.user, participation)
            streak_state = {
                "current": streak.current_count,
                "longest": streak.longest_count
            }
            
            # Phase 12: Evaluate badges
            earned_list = evaluate_after_participation(request.user, participation, streak)
            for b in earned_list:
                badges_earned.append({
                    "slug": b.slug,
                    "name": b.name,
                    "icon": b.icon
                })

            if xpt:
                request.user.refresh_from_db()
                xp_awarded = xpt.amount
                if request.user.current_level > old_level:
                    level_up = True

        active_count = session.participations.filter(status=Participation.Status.ACTIVE).count()
        if active_count == 0 and session.status == ActivitySession.Status.ACTIVE:
            session.status = ActivitySession.Status.ENDED
            session.ended_at = timezone.now()
            session.save()

        return Response({
            "detail": "Successfully left the session.",
            "xp_awarded": xp_awarded,
            "level_up": level_up,
            "current_level": request.user.current_level,
            "streak": streak_state,
            "badges_earned": badges_earned
        }, status=status.HTTP_200_OK)

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
    # Public map can be viewed by anyone, but maybe we require auth?
    # Prompt: "No API response or WebSocket-ready payload should accidentally include a private exact location."
    # Let's allow unauthenticated viewing (or maybe authenticated only?)
    # "Session mutations reject unauthenticated users." Map view might be authenticated. Let's use AllowAny or IsAuthenticated.
    # The specification says "Gravity is browsable...". Let's allow unauthenticated, but pass request.user if authenticated.
    
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
            
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
            return Response({"detail": "Impossible latitude/longitude bbox values."}, status=status.HTTP_400_BAD_REQUEST)
            
        bbox_polygon = Polygon.from_bbox((west, south, east, north))
        
        # Query active sessions within bbox
        sessions = ActivitySession.objects.filter(
            status=ActivitySession.Status.ACTIVE,
            activity_type__is_active=True,
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


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.conf import settings
import urllib.parse

class JoinTokenAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        session = get_object_or_404(ActivitySession, join_token=token)
        if session.status != ActivitySession.Status.ACTIVE:
            return Response({"detail": "This session is no longer active."}, status=status.HTTP_400_BAD_REQUEST)
        
        active_count = session.participations.filter(status=Participation.Status.ACTIVE).count()
        return Response({
            "activity": {
                "name": session.activity_type.name,
                "slug": session.activity_type.slug,
                "icon": session.activity_type.icon,
                "color": session.activity_type.color,
            },
            "label": session.label,
            "status": session.status,
            "participant_count": active_count,
            "started_at": session.started_at,
        })
        
    def post(self, request, token):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_403_FORBIDDEN)
            
        session = get_object_or_404(ActivitySession, join_token=token)
        
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
            join_method=Participation.JoinMethod.QR
        )

        return Response(ActivitySessionSerializer(session).data, status=status.HTTP_200_OK)


from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

class ParticipationMetricsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        participation = get_object_or_404(Participation, pk=pk)
        if participation.user != request.user:
            return Response({'detail': 'Not authorized to modify these metrics.'}, status=status.HTTP_403_FORBIDDEN)
            
        activity_type = participation.session.activity_type
        available_metrics = {m.slug: m for m in activity_type.metrics.all()}
        
        from .models import MetricValue
        
        updated_metrics = {}
        
        with transaction.atomic():
            for slug, value in request.data.items():
                if slug not in available_metrics:
                    raise ValidationError({slug: f"Metric '{slug}' is not valid for activity '{activity_type.slug}'"})
                
                metric = available_metrics[slug]
                if value is None:
                    continue # Or allow delete? Spec says submit metric, doesn't mention delete.
                    
                # Validate type
                try:
                    val_float = float(value)
                except (ValueError, TypeError):
                    raise ValidationError({slug: "Value must be numeric."})
                
                mv, created = MetricValue.objects.update_or_create(
                    participation=participation,
                    metric=metric,
                    defaults={'value': val_float}
                )
                
                try:
                    mv.clean()
                except DjangoValidationError as e:
                    raise ValidationError({slug: e.message_dict.get('value', str(e))})
                
                updated_metrics[slug] = mv.value
                
        return Response({'metrics': updated_metrics})

from django.db.models import Sum, Max, Avg, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

class LeaderboardAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, activity_slug, *args, **kwargs):
        activity_type = get_object_or_404(ActivityType, slug=activity_slug, is_active=True)
        period = request.GET.get('period', 'all')
        
        target_season = None
        
        from .logic.season_service import get_current_season
        from .models import Season, SeasonStanding
        
        if period == 'season':
            season_slug = request.GET.get('season')
            if season_slug:
                target_season = get_object_or_404(Season, slug=season_slug)
            else:
                target_season = get_current_season()
                
            if not target_season:
                # No current season available
                return Response({
                    "activity": {"slug": activity_type.slug, "name": activity_type.name, "icon": activity_type.icon},
                    "period": period,
                    "season": None,
                    "rows": [],
                    "me": None,
                    "detail": "No active season currently."
                })
        
        # If finalized season, use frozen standings
        primary_metric = activity_type.metrics.filter(is_primary=True, leaderboard_enabled=True).first() or activity_type.metrics.filter(leaderboard_enabled=True).first()
        
        rows = []
        if period == 'season' and target_season and target_season.finalized_at:
            standings = SeasonStanding.objects.filter(season=target_season, activity_type=activity_type).order_by('rank')
            for st in standings:
                rows.append({
                    "user": {
                        "id": st.user.id,
                        "username": st.user.username,
                        "display_name": getattr(st.user, 'display_name', None) or st.user.username,
                        "avatar_url": getattr(st.user, 'avatar_url', None)
                    },
                    "rank": st.rank,
                    "value": st.value
                })
        else:
            from .logic.leaderboard_service import compute_leaderboard
            computed_metric, computed_rows = compute_leaderboard(activity_type, period=period, target_season=target_season)
            primary_metric = computed_metric or primary_metric
            rows = computed_rows
            
        if not primary_metric:
            return Response({
                "activity": {"slug": activity_type.slug, "name": activity_type.name, "icon": activity_type.icon},
                "period": period,
                "rows": [],
                "me": None,
                "detail": "No leaderboard metric available."
            })
            
        # Apply limit and find 'me'
        limit = int(request.GET.get('limit', 100))
        final_rows = []
        me = None
        
        for r in rows:
            if len(final_rows) < limit:
                final_rows.append(r)
            if request.user.is_authenticated and r['user']['id'] == request.user.id:
                me = r
                
        resp = {
            "activity": {
                "slug": activity_type.slug,
                "name": activity_type.name,
                "icon": activity_type.icon
            },
            "metric": {
                "slug": primary_metric.slug,
                "name": primary_metric.name,
                "unit": primary_metric.unit
            },
            "period": period,
            "rows": final_rows,
            "me": me
        }
        
        if period == 'season' and target_season:
            resp["season"] = {
                "name": target_season.name,
                "slug": target_season.slug,
                "status": target_season.computed_status,
                "finalized": target_season.finalized_at is not None
            }
            
        return Response(resp)

class SeasonViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        from .models import Season
        return Season.objects.all().order_by('-starts_at')

    def get_serializer_class(self):
        from rest_framework import serializers
        from .models import Season
        
        class SeasonSerializer(serializers.ModelSerializer):
            status = serializers.CharField(source='computed_status', read_only=True)
            
            class Meta:
                model = Season
                fields = ['id', 'name', 'slug', 'description', 'starts_at', 'ends_at', 'is_enabled', 'status', 'finalized_at']
        return SeasonSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        from .logic.season_service import get_current_season
        season = get_current_season()
        if not season:
            return Response({"detail": "No active season."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(season)
        return Response(serializer.data)

class GravityEventViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        from .models import GravityEvent
        from django.utils import timezone
        
        qs = GravityEvent.objects.all().order_by('-starts_at')
        
        status_filter = self.request.query_params.get('status')
        now = timezone.now()
        
        if status_filter == 'live':
            qs = qs.filter(is_active=True, starts_at__lte=now, ends_at__gt=now)
        elif status_filter == 'upcoming':
            qs = qs.filter(is_active=True, starts_at__gt=now)
        elif status_filter == 'ended':
            qs = qs.filter(ends_at__lte=now)
            
        return qs

    def get_serializer_class(self):
        from rest_framework import serializers
        from .models import GravityEvent
        
        class GravityEventSerializer(serializers.ModelSerializer):
            activity_type_slug = serializers.CharField(source='activity_type.slug', read_only=True, allow_null=True)
            activity_type_name = serializers.CharField(source='activity_type.name', read_only=True, allow_null=True)
            status = serializers.CharField(source='computed_status', read_only=True)
            badge_icon = serializers.CharField(source='badge.icon', read_only=True, allow_null=True)
            
            class Meta:
                model = GravityEvent
                fields = [
                    'id', 'name', 'slug', 'description', 'icon',
                    'starts_at', 'ends_at', 'is_active', 'status',
                    'activity_type_slug', 'activity_type_name',
                    'xp_multiplier', 'flat_xp_bonus', 'badge_icon'
                ]
        return GravityEventSerializer

from rest_framework.views import APIView
from .logic.pulse_service import get_pulse_now

class PulseNowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lat_str = request.query_params.get('lat')
        lng_str = request.query_params.get('lng')

        if lat_str is None or lng_str is None:
            return Response({"detail": "Both lat and lng query parameters are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid latitude or longitude value."}, status=status.HTTP_400_BAD_REQUEST)

        radius = None
        radius_str = request.query_params.get('radius')
        if radius_str is not None:
            try:
                radius = float(radius_str)
                if radius <= 0:
                    return Response({"detail": "Radius must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({"detail": "Invalid radius parameter."}, status=status.HTTP_400_BAD_REQUEST)

        limit = 20
        limit_str = request.query_params.get('limit')
        if limit_str is not None:
            try:
                limit = int(limit_str)
                if limit <= 0:
                    return Response({"detail": "Limit must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({"detail": "Invalid limit parameter."}, status=status.HTTP_400_BAD_REQUEST)

        activity_slug = request.query_params.get('activity')

        try:
            data = get_pulse_now(
                user=request.user,
                lat=lat,
                lng=lng,
                radius_m=radius,
                activity_slug=activity_slug,
                limit=limit
            )
            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
