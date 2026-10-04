import { apiClient } from './client';

export interface AreaHistoryQuery {
  lat: number;
  lng: number;
  radius_m?: number;
  period?: 'today' | '7d' | '30d' | '90d' | 'season' | 'all';
}

export interface ActivityShare {
  activity_type_id: number;
  name: string;
  slug: string;
  icon: string;
  color: string;
  participation_count: number;
  session_count: number;
  unique_participants: number;
  share_percentage: number;
}

export interface TimeBucket {
  label: string;
  start_hour: number;
  end_hour: number;
  participation_count: number;
  session_count: number;
}

export interface WeekdayDistribution {
  day: string;
  day_index: number;
  participation_count: number;
  session_count: number;
}

export interface AreaHistoryResponse {
  query: {
    lat: number;
    lng: number;
    radius_m: number;
    period: string;
  };
  privacy_suppressed: boolean;
  message: string;
  min_participants_required: number;
  total_sessions: number;
  total_participations: number;
  total_unique_participants: number;
  dominant_activity: ActivityShare | null;
  activities: ActivityShare[];
  time_distribution: TimeBucket[];
  peak_time: string | null;
  weekday_distribution: WeekdayDistribution[];
  busiest_day: string | null;
}

export const getAreaHistory = async (params: AreaHistoryQuery): Promise<AreaHistoryResponse> => {
  const queryParams: Record<string, any> = {
    lat: params.lat,
    lng: params.lng,
  };
  if (params.radius_m !== undefined) {
    queryParams.radius = params.radius_m;
  }
  if (params.period) {
    queryParams.period = params.period;
  }

  const response = await apiClient.get<AreaHistoryResponse>('/history/area/', {
    params: queryParams,
  });
  return response.data;
};
