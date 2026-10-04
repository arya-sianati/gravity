import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import { requestCurrentLocation } from '../../lib/map/geolocation';
import { getActivities } from '../../api/activities';
import type { ActivityType } from '../../api/activities';
import { getLiveMap } from '../../api/map';
import type { LiveMapFeatureCollection } from '../../api/map';
import { MapControls } from './MapControls';

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL || 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const FALLBACK_CENTER: [number, number] = [-98.5795, 39.8283];

interface GravityMapProps {}

export const GravityMap: React.FC<GravityMapProps> = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);
  const dataRef = useRef<LiveMapFeatureCollection | null>(null);

  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [bbox, setBbox] = useState<number[] | null>(null);
  
  // Filtering
  const [hiddenActivities, setHiddenActivities] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (mapRef.current) return;

    mapRef.current = new maplibregl.Map({
      container: mapContainerRef.current!,
      style: STYLE_URL,
      center: FALLBACK_CENTER,
      zoom: 3,
      interactive: true
    });

    mapRef.current.on('load', () => {
      getActivities().then(data => {
        setActivities(data);
        data.forEach(act => {
          const sourceId = `heat-source-${act.slug}`;
          const layerId = `heat-layer-${act.slug}`;
          
          if (!mapRef.current!.getSource(sourceId)) {
            mapRef.current!.addSource(sourceId, {
              type: 'geojson',
              data: { type: 'FeatureCollection', features: [] }
            });
            
            mapRef.current!.addLayer({
              id: layerId,
              type: 'heatmap',
              source: sourceId,
              paint: {
                'heatmap-weight': [
                  'interpolate', ['linear'], ['get', 'weight'],
                  0, 0,
                  10, 1
                ],
                'heatmap-intensity': [
                  'interpolate', ['linear'], ['zoom'],
                  0, 1,
                  15, 3
                ],
                'heatmap-color': [
                  'interpolate', ['linear'], ['heatmap-density'],
                  0, 'rgba(0, 0, 0, 0)',
                  0.2, act.color + '33',
                  0.6, act.color + '99',
                  1, act.color
                ],
                'heatmap-radius': [
                  'interpolate', ['linear'], ['zoom'],
                  0, 15,
                  15, 40
                ],
                'heatmap-opacity': 0.8
              }
            });
          }
        });
      }).catch(err => console.error("Failed to load activities for map prep", err));
      
      handleRecenter();
    });

    let timeout: ReturnType<typeof setTimeout>;
    mapRef.current.on('moveend', () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        if (!mapRef.current) return;
        const bounds = mapRef.current.getBounds();
        setBbox([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
      }, 500);
    });

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  const handleRecenter = useCallback(() => {
    setLocating(true);
    setGeoError(null);
    requestCurrentLocation(
      (loc) => {
        setLocating(false);
        if (mapRef.current) {
          mapRef.current.flyTo({ center: [loc.longitude, loc.latitude], zoom: 14, essential: true });
          if (!userMarkerRef.current) {
            const el = document.createElement('div');
            el.className = 'w-4 h-4 bg-blue-500 border-2 border-white rounded-full shadow-[0_0_10px_rgba(59,130,246,0.8)]';
            userMarkerRef.current = new maplibregl.Marker({ element: el }).setLngLat([loc.longitude, loc.latitude]).addTo(mapRef.current);
          } else {
            userMarkerRef.current.setLngLat([loc.longitude, loc.latitude]);
          }
        }
      },
      (err) => {
        setLocating(false);
        let msg = "Location unavailable.";
        if (err.code === 1) msg = "Location permission denied.";
        else if (err.code === 2) msg = "Position unavailable.";
        else if (err.code === 3) msg = "Location request timed out.";
        setGeoError(msg);
      }
    );
  }, []);

  useEffect(() => {
    if (!bbox || activities.length === 0) return;

    const fetchLiveHeat = async () => {
      try {
        const liveData = await getLiveMap(bbox);
        dataRef.current = liveData;

        activities.forEach(act => {
          const sourceId = `heat-source-${act.slug}`;
          const source = mapRef.current?.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
          if (source) {
            if (hiddenActivities.has(act.slug)) {
              source.setData({ type: 'FeatureCollection', features: [] });
            } else {
              const filteredFeatures = liveData.features.filter(f => f.properties.activity_slug === act.slug);
              source.setData({ type: 'FeatureCollection', features: filteredFeatures });
            }
          }
        });
      } catch (err) {
        console.error("Failed to fetch live heat map", err);
      }
    };

    fetchLiveHeat();
    const interval = setInterval(fetchLiveHeat, 15000);
    return () => clearInterval(interval);
  }, [bbox, activities, hiddenActivities]);

  const toggleActivityFilter = (slug: string) => {
    setHiddenActivities(prev => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      {geoError && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-gray-900 bg-opacity-80 text-white px-4 py-2 rounded-full text-sm shadow-md pointer-events-none transition-opacity">
          {geoError}
        </div>
      )}
      
      {/* Filters Overlay */}
      <div className="absolute top-4 right-4 z-10 flex flex-wrap gap-2 justify-end max-w-[70%]">
        {activities.map(act => {
          const isHidden = hiddenActivities.has(act.slug);
          return (
            <button
              key={act.slug}
              onClick={() => toggleActivityFilter(act.slug)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border shadow-sm transition-colors ${
                isHidden 
                  ? 'bg-gray-800 border-gray-700 text-gray-500 opacity-70' 
                  : 'bg-gray-900 border-gray-600 text-white'
              }`}
              style={{ borderLeftColor: isHidden ? undefined : act.color, borderLeftWidth: isHidden ? 1 : 4 }}
            >
              {act.icon} {act.name}
            </button>
          );
        })}
      </div>

      <div ref={mapContainerRef} className="flex-1 w-full" />
      <MapControls onRecenter={handleRecenter} locating={locating} />
    </div>
  );
};
