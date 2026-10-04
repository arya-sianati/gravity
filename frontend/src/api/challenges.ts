import { apiClient } from './client';
import type { ActivityType, ActivityMetric } from './activities';

export interface ChallengeUser {
  id: number;
  username: string;
  display_name: string | null;
}

export interface ChallengeParticipant {
  id: number;
  user: ChallengeUser;
  invitation_status: 'invited' | 'accepted' | 'declined';
  joined_at: string | null;
  progress: number;
  is_winner: boolean;
  rank: number | null;
}

export interface FriendChallenge {
  id: number;
  title: string;
  created_by: ChallengeUser;
  activity_type: ActivityType;
  metric: ActivityMetric;
  challenge_type: 'first_to_target' | 'highest_by_deadline' | 'cooperative_target';
  target_value: number | null;
  starts_at: string;
  ends_at: string;
  status: 'pending' | 'active' | 'completed' | 'cancelled' | 'expired';
  winner: ChallengeUser | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  participants: ChallengeParticipant[];
  my_participant_info: ChallengeParticipant | null;
  combined_progress: number | null;
}

export interface ChallengeCreatePayload {
  activity_type: string | number;
  metric: string | number;
  challenge_type: 'first_to_target' | 'highest_by_deadline' | 'cooperative_target';
  target_value?: number | null;
  starts_at: string;
  ends_at: string;
  invitees: number[];
  title?: string;
}

export const getChallenges = async (statusFilter?: string): Promise<FriendChallenge[]> => {
  let url = '/challenges/';
  if (statusFilter) {
    url += `?status=${statusFilter}`;
  }
  const response = await apiClient.get<FriendChallenge[]>(url);
  return response.data;
};

export const getChallengeDetail = async (id: number): Promise<FriendChallenge> => {
  const response = await apiClient.get<FriendChallenge>(`/challenges/${id}/`);
  return response.data;
};

export const createChallenge = async (payload: ChallengeCreatePayload): Promise<FriendChallenge> => {
  const response = await apiClient.post<FriendChallenge>('/challenges/', payload);
  return response.data;
};

export const acceptChallenge = async (id: number): Promise<FriendChallenge> => {
  const response = await apiClient.post<FriendChallenge>(`/challenges/${id}/accept/`);
  return response.data;
};

export const declineChallenge = async (id: number): Promise<FriendChallenge> => {
  const response = await apiClient.post<FriendChallenge>(`/challenges/${id}/decline/`);
  return response.data;
};

export const cancelChallenge = async (id: number): Promise<FriendChallenge> => {
  const response = await apiClient.post<FriendChallenge>(`/challenges/${id}/cancel/`);
  return response.data;
};
