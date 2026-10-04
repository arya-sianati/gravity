import { apiClient } from './client';

export interface ActivityMetric {
  id: number;
  name: string;
  slug: string;
  unit: string;
  data_type: 'integer' | 'decimal' | 'duration' | 'boolean';
  aggregation: 'sum' | 'max' | 'average' | 'latest';
  is_primary: boolean;
  leaderboard_enabled: boolean;
  required: boolean;
  min_value: number | null;
  max_value: number | null;
}

export interface ActivityType {
  id: number;
  name: string;
  slug: string;
  icon: string;
  color: string;
  description: string;
  cluster_radius_m: number;
  qr_join_enabled: boolean;
  self_start_enabled: boolean;
  gps_tracking_enabled: boolean;
  auto_stop_enabled?: boolean;
  auto_stop_mode?: 'disabled' | 'anchor_radius' | 'inactivity';
  auto_stop_radius_m?: number;
  auto_stop_grace_seconds?: number;
  metrics: ActivityMetric[];
}

export const getActivities = async (): Promise<ActivityType[]> => {
  const response = await apiClient.get<ActivityType[]>('/activity-types/');
  return response.data;
};

export const getActivity = async (slug: string): Promise<ActivityType> => {
  const response = await apiClient.get<ActivityType>(`/activity-types/${slug}/`);
  return response.data;
};
