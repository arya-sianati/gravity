from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    UserProfileUpdateSerializer,
)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class CSRFEnforcedAPIView(APIView):
    """
    Ensures CSRF validation is performed on unsafe methods even if the
    user is not yet authenticated via session.
    """
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            SessionAuthentication().enforce_csrf(request)


class RegisterView(CSRFEnforcedAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(CSRFEnforcedAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

class XPHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from activities.models import XPTransaction
        # Simple pagination for history
        qs = XPTransaction.objects.filter(user=request.user).order_by('-created_at')[:50]
        data = []
        for xpt in qs:
            data.append({
                "id": xpt.id,
                "amount": xpt.amount,
                "reason": xpt.reason,
                "description": xpt.description,
                "activity_type": xpt.activity_type.name if xpt.activity_type else None,
                "created_at": xpt.created_at.isoformat()
            })
        return Response(data, status=status.HTTP_200_OK)

class MyBadgesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from activities.models import UserBadge
        user_badges = UserBadge.objects.filter(user=request.user).select_related('badge', 'activity_type').order_by('-earned_at')
        
        data = []
        for ub in user_badges:
            data.append({
                "slug": ub.badge.slug,
                "name": ub.badge.name,
                "description": ub.badge.description,
                "icon": ub.badge.icon,
                "earned_at": ub.earned_at.isoformat(),
                "activity_type": ub.activity_type.name if ub.activity_type else None
            })
        
        # Also return streak stats for profile rendering convenience
        from activities.models import Streak
        from activities.logic.streak_service import get_effective_streak
        streak = Streak.objects.filter(user=request.user).first()
        streak_data = {
            "current": get_effective_streak(streak),
            "longest": streak.longest_count if streak else 0
        }
        
        return Response({
            "badges": data,
            "streak": streak_data
        }, status=status.HTTP_200_OK)


from django.shortcuts import get_object_or_404
from django.db.models import Q
from accounts.models import User, Friendship
from accounts.serializers import PublicUserSerializer, FriendshipRequestSerializer
from accounts.logic.friend_service import (
    request_friendship,
    accept_friendship,
    decline_friendship,
    cancel_friendship_request,
    remove_friendship,
    get_friends_for_user,
    get_incoming_requests_for_user,
    get_outgoing_requests_for_user,
    get_friends_presence,
)
from activities.models import Participation, ActivitySession, Streak, UserBadge
from activities.logic.streak_service import get_effective_streak
from activities.logic.privacy_service import resolve_location_visibility, generalize_location, Visibility


class UserSearchView(APIView):
    """
    Search for users by username or display_name.
    Only returns public safe fields (id, username, display_name, current_level, friendship_status).
    No email or location coordinates are ever exposed.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([], status=status.HTTP_200_OK)

        users = User.objects.filter(
            Q(username__icontains=query) | Q(display_name__icontains=query),
            is_active=True
        ).exclude(id=request.user.id)[:20]

        serializer = PublicUserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicProfileView(APIView):
    """
    Retrieves public profile information for a user:
    - Safe identity fields & friendship status
    - Badges earned
    - Streak statistics
    - Active session presence (strictly gated by central privacy resolver)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id, is_active=True)

        user_data = PublicUserSerializer(target_user, context={'request': request}).data

        # Streak
        streak = Streak.objects.filter(user=target_user).first()
        streak_data = {
            "current": get_effective_streak(streak),
            "longest": streak.longest_count if streak else 0
        }

        # Badges
        user_badges = UserBadge.objects.filter(user=target_user).select_related('badge', 'activity_type').order_by('-earned_at')
        badges_data = [{
            "slug": ub.badge.slug,
            "name": ub.badge.name,
            "description": ub.badge.description,
            "icon": ub.badge.icon,
            "earned_at": ub.earned_at.isoformat(),
            "activity_type": ub.activity_type.name if ub.activity_type else None
        } for ub in user_badges]

        # Active session context (privacy-gated)
        active_part = Participation.objects.filter(
            user=target_user,
            status=Participation.Status.ACTIVE,
            session__status=ActivitySession.Status.ACTIVE,
            session__activity_type__is_active=True
        ).select_related('session', 'session__activity_type').first()

        active_session_data = None
        if active_part:
            session = active_part.session
            visibility = resolve_location_visibility(target_user, request.user)
            if visibility != Visibility.HIDDEN:
                if visibility == Visibility.EXACT:
                    loc = {"lat": session.location.y, "lng": session.location.x, "mode": "exact"}
                else:
                    gen_pt = generalize_location(session.location)
                    loc = {"lat": gen_pt.y, "lng": gen_pt.x, "mode": "blurred"}

                active_session_data = {
                    "id": str(session.id),
                    "activity_type": {
                        "slug": session.activity_type.slug,
                        "name": session.activity_type.name,
                        "icon": session.activity_type.icon,
                        "color": session.activity_type.color,
                    },
                    "label": session.label,
                    "started_at": active_part.joined_at.isoformat() if active_part.joined_at else session.created_at.isoformat(),
                    "location": loc,
                    "visibility": visibility
                }

        return Response({
            "user": user_data,
            "streak": streak_data,
            "badges": badges_data,
            "active_session": active_session_data
        }, status=status.HTTP_200_OK)


class FriendshipRequestView(APIView):
    """
    Sends a friend request to a target user (by user_id or username).
    Handles reciprocal auto-accept and duplicate requests gracefully.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        username = request.data.get('username')

        if not user_id and not username:
            return Response({"detail": "user_id or username is required."}, status=status.HTTP_400_BAD_REQUEST)

        if user_id:
            try:
                target_user = User.objects.get(id=user_id, is_active=True)
            except (User.DoesNotExist, ValueError):
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                target_user = User.objects.get(username__iexact=username, is_active=True)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.id == request.user.id:
            return Response({"detail": "Cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            friendship, outcome = request_friendship(request.user, target_user)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FriendshipRequestSerializer(friendship, context={'request': request})
        res_status = status.HTTP_201_CREATED if outcome in ['requested', 'accepted'] else status.HTTP_200_OK
        return Response({
            "action_result": outcome,
            "friendship": serializer.data
        }, status=res_status)


class IncomingFriendRequestsView(APIView):
    """
    Lists pending friend requests sent to the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = get_incoming_requests_for_user(request.user)
        serializer = FriendshipRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class OutgoingFriendRequestsView(APIView):
    """
    Lists pending friend requests initiated by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = get_outgoing_requests_for_user(request.user)
        serializer = FriendshipRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcceptFriendRequestView(APIView):
    """
    Accepts an incoming friend request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            friendship = accept_friendship(request.user, pk)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        serializer = FriendshipRequestSerializer(friendship, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeclineFriendRequestView(APIView):
    """
    Declines an incoming friend request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            friendship = decline_friendship(request.user, pk)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        serializer = FriendshipRequestSerializer(friendship, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CancelFriendRequestView(APIView):
    """
    Cancels an outgoing friend request initiated by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            cancel_friendship_request(request.user, pk)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response({"detail": "Friend request cancelled."}, status=status.HTTP_200_OK)


class RemoveFriendView(APIView):
    """
    Removes an accepted friendship. Supports DELETE /api/friends/<user_id>/ and POST /api/friends/<user_id>/remove/.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id, is_active=True)
        try:
            removed = remove_friendship(request.user, target_user)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not removed:
            return Response({"detail": "No active friendship found with this user."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Friend removed successfully."}, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        return self.delete(request, user_id)


class FriendsListView(APIView):
    """
    Lists accepted friends of the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = get_friends_for_user(request.user)
        serializer = PublicUserSerializer(friends, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FriendsPresenceView(APIView):
    """
    Returns active live presence of accepted friends.
    Location and distance are resolved using the central privacy resolver.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        lat_val = None
        lng_val = None
        if lat is not None and lng is not None:
            try:
                lat_val = float(lat)
                lng_val = float(lng)
            except ValueError:
                pass

        presence = get_friends_presence(request.user, viewer_lat=lat_val, viewer_lng=lng_val)
        return Response(presence, status=status.HTTP_200_OK)
