import { apiClient } from './client';

export interface PublicUser {
  id: number;
  username: string;
  display_name: string | null;
  current_level: number;
  friendship_status: 'self' | 'none' | 'pending_outgoing' | 'pending_incoming' | 'accepted' | 'blocked';
}

export interface FriendshipRequest {
  id: number;
  status: 'pending' | 'accepted' | 'declined' | 'blocked';
  initiator: PublicUser;
  recipient: PublicUser;
  created_at: string;
  updated_at: string;
}

export interface FriendPresenceItem {
  friend: {
    id: number;
    username: string;
    display_name: string;
    current_level: number;
    avatar_url: string | null;
  };
  session_id: string;
  activity: {
    slug: string;
    name: string;
    icon: string;
    color: string;
  };
  label: string | null;
  started_at: string;
  location_display: string | null;
  visibility_mode: 'hidden' | 'blurred' | 'exact';
}

export interface PublicProfileResponse {
  user: PublicUser;
  streak: {
    current: number;
    longest: number;
  };
  badges: Array<{
    slug: string;
    name: string;
    description: string;
    icon: string;
    earned_at: string;
    activity_type: string | null;
  }>;
  active_session: {
    id: string;
    activity_type: {
      slug: string;
      name: string;
      icon: string;
      color: string;
    };
    label: string | null;
    started_at: string;
    location: {
      lat: number;
      lng: number;
      mode: 'exact' | 'blurred';
    };
    visibility: 'hidden' | 'blurred' | 'exact';
  } | null;
}

export const searchUsers = async (query: string): Promise<PublicUser[]> => {
  const trimmed = query.trim();
  if (!trimmed) return [];
  const response = await apiClient.get<PublicUser[]>(`/users/search/?q=${encodeURIComponent(trimmed)}`);
  return response.data;
};

export const getUserProfile = async (userId: number): Promise<PublicProfileResponse> => {
  const response = await apiClient.get<PublicProfileResponse>(`/users/${userId}/profile/`);
  return response.data;
};

export const getFriends = async (): Promise<PublicUser[]> => {
  const response = await apiClient.get<PublicUser[]>('/friends/');
  return response.data;
};

export const getFriendsPresence = async (lat?: number, lng?: number): Promise<FriendPresenceItem[]> => {
  let url = '/friends/presence/';
  if (lat !== undefined && lng !== undefined) {
    url += `?lat=${lat}&lng=${lng}`;
  }
  const response = await apiClient.get<FriendPresenceItem[]>(url);
  return response.data;
};

export const sendFriendRequest = async (userId: number): Promise<{ action_result: string; friendship: FriendshipRequest }> => {
  const response = await apiClient.post<{ action_result: string; friendship: FriendshipRequest }>('/friends/request/', { user_id: userId });
  return response.data;
};

export const getIncomingFriendRequests = async (): Promise<FriendshipRequest[]> => {
  const response = await apiClient.get<FriendshipRequest[]>('/friends/requests/incoming/');
  return response.data;
};

export const getOutgoingFriendRequests = async (): Promise<FriendshipRequest[]> => {
  const response = await apiClient.get<FriendshipRequest[]>('/friends/requests/outgoing/');
  return response.data;
};

export const acceptFriendRequest = async (requestId: number): Promise<FriendshipRequest> => {
  const response = await apiClient.post<FriendshipRequest>(`/friends/requests/${requestId}/accept/`);
  return response.data;
};

export const declineFriendRequest = async (requestId: number): Promise<FriendshipRequest> => {
  const response = await apiClient.post<FriendshipRequest>(`/friends/requests/${requestId}/decline/`);
  return response.data;
};

export const cancelFriendRequest = async (requestId: number): Promise<{ detail: string }> => {
  const response = await apiClient.post<{ detail: string }>(`/friends/requests/${requestId}/cancel/`);
  return response.data;
};

export const removeFriend = async (userId: number): Promise<{ detail: string }> => {
  const response = await apiClient.delete<{ detail: string }>(`/friends/${userId}/`);
  return response.data;
};
