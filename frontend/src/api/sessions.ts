import { apiClient } from './client';
import type { ActivityType } from './activities';

export interface Participant {
  id: number;
  username: string;
  display_name: string;
}

export interface ParticipationData {
  id: number;
  user: Participant;
  status: string;
  joined_at: string;
  join_method: string;
  metrics: Record<string, number>;
}

export interface ActivitySession {
  id: string;
  activity_type: number;
  activity_type_details: ActivityType;
  created_by: Participant;
  status: 'active' | 'ended' | 'cancelled';
  label: string | null;
  started_at: string;
  ended_at: string | null;
  active_participants_count: number;
  my_participation: ParticipationData | null;
}

export interface NearbySession {
  id: string;
  activity_type_slug: string;
  status: string;
  started_at: string;
  active_participants_count: number;
  distance_m: number;
}

export const startSession = async (activityType: number, lat: number, lng: number, label?: string): Promise<ActivitySession> => {
  const payload = { activity_type: activityType, lat, lng, label };
  const response = await apiClient.post<ActivitySession>('/sessions/', payload);
  return response.data;
};

export const joinSession = async (sessionId: string, params?: { source?: string }): Promise<ActivitySession> => {
  const response = await apiClient.post<ActivitySession>(`/sessions/${sessionId}/join/`, params || {});
  return response.data;
};

export interface LeaveSessionResponse {
  detail: string;
  xp_awarded: number | null;
  level_up: boolean;
  current_level: number;
  streak: { current: number, longest: number } | null;
  badges_earned: { slug: string, name: string, icon: string }[];
}

export const leaveSession = async (sessionId: string): Promise<LeaveSessionResponse> => {
  const res = await apiClient.post<LeaveSessionResponse>(`/sessions/${sessionId}/leave/`);
  return res.data;
};

export interface HeartbeatResponse {
  participation_status: string;
  inside_activity_area: boolean;
  outside_since: string | null;
  grace_remaining_seconds: number | null;
  auto_stopped: boolean;
  already_concluded?: boolean;
  completion?: LeaveSessionResponse;
}

export const sendActivityHeartbeat = async (lat: number, lng: number): Promise<HeartbeatResponse> => {
  const response = await apiClient.post<HeartbeatResponse>('/me/activity-location/', { lat, lng });
  return response.data;
};

export const getNearbySessions = async (activitySlug: string, lat: number, lng: number): Promise<NearbySession[]> => {
  const response = await apiClient.get<NearbySession[]>('/sessions/nearby/', {
    params: { activity: activitySlug, lat, lng }
  });
  return response.data;
};

export const getActiveParticipation = async (): Promise<ActivitySession | null> => {
  const response = await apiClient.get<ActivitySession | null>('/me/active-participation/');
  return response.data;
};

export const getJoinCode = async (sessionId: string): Promise<{ join_url: string; expires_at: string | null }> => {
  const response = await apiClient.get(`/sessions/${sessionId}/join-code/`);
  return response.data;
};

export const getJoinPreview = async (token: string): Promise<any> => {
  const response = await apiClient.get(`/join/${token}/`);
  return response.data;
};

export const joinByToken = async (token: string): Promise<any> => {
  const response = await apiClient.post(`/join/${token}/`);
  return response.data;
};


export const updateMetrics = async (participationId: number, metrics: Record<string, number | null>): Promise<{metrics: Record<string, number>}> => {
  const response = await apiClient.patch(`/participations/${participationId}/metrics/`, metrics);
  return response.data;
};
