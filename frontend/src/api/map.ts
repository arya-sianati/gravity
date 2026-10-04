import { apiClient } from './client';

export interface LiveMapFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    session_id: string;
    activity_slug: string;
    participant_count: number;
    weight: number;
  };
}

export interface LiveMapFeatureCollection {
  type: 'FeatureCollection';
  features: LiveMapFeature[];
}

export const getLiveMap = async (bbox: number[]): Promise<LiveMapFeatureCollection> => {
  const response = await apiClient.get<LiveMapFeatureCollection>('/map/live/', {
    params: { bbox: bbox.join(',') }
  });
  return response.data;
};
