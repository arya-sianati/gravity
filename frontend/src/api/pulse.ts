import { apiClient } from './client';

export interface PulseItem {
  session_id: string;
  activity: {
    slug: string;
    name: string;
    icon: string;
    color: string;
  };
  label: string | null;
  participant_count: number;
  started_at: string;
  distance: {
    display: string;
  };
  pulse_score: number;
  can_join: boolean;
  event: {
    id: number;
    name: string;
    xp_multiplier: number;
    flat_xp_bonus: number;
    badge_icon?: string | null;
  } | null;
}

export interface PulseNowResponse {
  items: PulseItem[];
  search_radius_m: number;
}

export interface PulseNowParams {
  lat: number;
  lng: number;
  radius?: number;
  activity?: string;
  limit?: number;
}

export const getPulseNow = async (params: PulseNowParams): Promise<PulseNowResponse> => {
  const response = await apiClient.get<PulseNowResponse>('/api/pulse/now/', { params });
  return response.data;
};
