from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    CsrfView,
    XPHistoryAPIView,
    MyBadgesAPIView,
    UserSearchView,
    PublicProfileView,
    FriendshipRequestView,
    IncomingFriendRequestsView,
    OutgoingFriendRequestsView,
    AcceptFriendRequestView,
    DeclineFriendRequestView,
    CancelFriendRequestView,
    RemoveFriendView,
    FriendsListView,
    FriendsPresenceView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', LoginView.as_view(), name='auth_login'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/csrf/', CsrfView.as_view(), name='auth_csrf'),
    path('me/', MeView.as_view(), name='me'),
    path('me/xp-history/', XPHistoryAPIView.as_view(), name='xp-history'),
    path('me/badges/', MyBadgesAPIView.as_view(), name='my-badges'),

    # Phase 16: Friends & User Search
    path('users/search/', UserSearchView.as_view(), name='user-search'),
    path('users/<int:user_id>/profile/', PublicProfileView.as_view(), name='user-profile'),

    path('friends/', FriendsListView.as_view(), name='friends-list'),
    path('friends/presence/', FriendsPresenceView.as_view(), name='friends-presence'),
    path('friends/request/', FriendshipRequestView.as_view(), name='friend-request'),
    path('friends/requests/incoming/', IncomingFriendRequestsView.as_view(), name='friend-requests-incoming'),
    path('friends/requests/outgoing/', OutgoingFriendRequestsView.as_view(), name='friend-requests-outgoing'),
    path('friends/requests/<int:pk>/accept/', AcceptFriendRequestView.as_view(), name='friend-request-accept'),
    path('friends/requests/<int:pk>/decline/', DeclineFriendRequestView.as_view(), name='friend-request-decline'),
    path('friends/requests/<int:pk>/cancel/', CancelFriendRequestView.as_view(), name='friend-request-cancel'),
    path('friends/<int:user_id>/', RemoveFriendView.as_view(), name='friend-remove'),
    path('friends/<int:user_id>/remove/', RemoveFriendView.as_view(), name='friend-remove-post'),
]
