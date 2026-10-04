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
