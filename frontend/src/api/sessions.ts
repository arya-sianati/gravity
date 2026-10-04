import { apiClient } from './client';
import type { ActivityType } from './activities';

export interface Participant {
  id: number;
  username: string;
  display_name: string;
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
  const response = await apiClient.post<ActivitySession>('/api/sessions/', payload);
  return response.data;
};

export const joinSession = async (sessionId: string): Promise<ActivitySession> => {
  const response = await apiClient.post<ActivitySession>(`/api/sessions/${sessionId}/join/`);
  return response.data;
};

export const leaveSession = async (sessionId: string): Promise<void> => {
  await apiClient.post(`/api/sessions/${sessionId}/leave/`);
};

export const getNearbySessions = async (activitySlug: string, lat: number, lng: number): Promise<NearbySession[]> => {
  const response = await apiClient.get<NearbySession[]>('/api/sessions/nearby/', {
    params: { activity: activitySlug, lat, lng }
  });
  return response.data;
};

export const getActiveParticipation = async (): Promise<ActivitySession | null> => {
  const response = await apiClient.get<ActivitySession | null>('/api/me/active-participation/');
  return response.data;
};
