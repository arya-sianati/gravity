import { apiClient } from './client';

export interface Season {
  id: number;
  name: string;
  slug: string;
  description: string;
  starts_at: string;
  ends_at: string;
  is_enabled: boolean;
  status: string;
  finalized_at: string | null;
}

export const getSeasons = async (): Promise<Season[]> => {
  const response = await apiClient.get<Season[]>('/api/seasons/');
  return response.data;
};

export const getCurrentSeason = async (): Promise<Season> => {
  const response = await apiClient.get<Season>('/api/seasons/current/');
  return response.data;
};
