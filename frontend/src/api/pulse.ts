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
  const response = await apiClient.get<PulseNowResponse>('/pulse/now/', { params });
  return response.data;
};

export interface PulseSoonItem {
  activity: {
    id: number;
    slug: string;
    name: string;
    icon: string;
    color: string;
  };
  area: {
    lat: number;
    lng: number;
    radius_m: number;
  };
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  distance: {
    raw_m: number;
    display: string;
  };
  expected_window: {
    starts_at: string;
    ends_at: string;
    display: string;
  };
  confidence_score: number;
  confidence_level: 'moderate' | 'strong' | 'very_strong';
  confidence_display: string;
  historical_evidence: {
    matching_weeks: number;
    total_lookback_weeks: number;
    observations: number;
    typical_participants: number;
    unique_users: number;
  };
  reason: string;
  event: {
    name: string;
    slug: string;
    xp_multiplier: number;
    flat_xp_bonus: number;
    badge_icon?: string | null;
  } | null;
}

export interface PulseSoonResponse {
  items: PulseSoonItem[];
}

export interface PulseSoonParams {
  lat: number;
  lng: number;
  radius?: number;
  horizon_minutes?: number;
  activity?: string;
  limit?: number;
}

export const getPulseSoon = async (params: PulseSoonParams): Promise<PulseSoonResponse> => {
  const response = await apiClient.get<PulseSoonResponse>('/pulse/soon/', { params });
  return response.data;
};
