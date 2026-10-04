from django.urls import path
from .views import RegisterView, LoginView, LogoutView, MeView, CsrfView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', LoginView.as_view(), name='auth_login'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/csrf/', CsrfView.as_view(), name='auth_csrf'),
    path('me/', MeView.as_view(), name='me'),
]
