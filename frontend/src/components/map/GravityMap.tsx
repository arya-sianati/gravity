import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import { requestCurrentLocation } from '../../lib/map/geolocation';
import { getActivities } from '../../api/activities';
import type { ActivityType } from '../../api/activities';
import { MapControls } from './MapControls';

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL || 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const FALLBACK_CENTER: [number, number] = [-98.5795, 39.8283]; // Center of US

interface GravityMapProps {
  // Placeholder for future props
}

export const GravityMap: React.FC<GravityMapProps> = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);

  const [, setActivities] = useState<ActivityType[]>([]);
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  
  // Viewport tracking (Phase 07 preparation)
  const [, setBbox] = useState<number[] | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    mapRef.current = new maplibregl.Map({
      container: mapContainerRef.current,
      style: STYLE_URL,
      center: FALLBACK_CENTER,
      zoom: 3, // Zoomed out by default until location is found
      attributionControl: false,
    });

    mapRef.current.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    mapRef.current.on('load', () => {
      // Prepare sources and layers for activities (Phase 07 prep)
      getActivities().then(data => {
        setActivities(data);
        if (!mapRef.current) return;
        
        data.forEach(act => {
          const sourceId = `heat-source-${act.slug}`;
          const layerId = `heat-layer-${act.slug}`;
          
          if (!mapRef.current!.getSource(sourceId)) {
            mapRef.current!.addSource(sourceId, {
              type: 'geojson',
              data: { type: 'FeatureCollection', features: [] }
            });
            
            // Empty layer placeholder for future live heat
            mapRef.current!.addLayer({
              id: layerId,
              type: 'heatmap',
              source: sourceId,
              paint: {
                'heatmap-color': [
                  'interpolate', ['linear'], ['heatmap-density'],
                  0, 'rgba(0,0,0,0)',
                  1, act.color
                ]
              }
            });
          }
        });
      }).catch(err => console.error("Failed to load activities for map prep", err));
      
      // Auto-request location on load
      handleRecenter();
    });

    // Viewport tracking with debounce
    let timeout: ReturnType<typeof setTimeout>;
    mapRef.current.on('moveend', () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        if (!mapRef.current) return;
        const bounds = mapRef.current.getBounds();
        setBbox([
          bounds.getWest(),
          bounds.getSouth(),
          bounds.getEast(),
          bounds.getNorth()
        ]);
        // Phase 07: Fire GET /api/map/live/?bbox=... here
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
          mapRef.current.flyTo({
            center: [loc.longitude, loc.latitude],
            zoom: 14,
            essential: true
          });

          // Update user marker
          if (!userMarkerRef.current) {
            const el = document.createElement('div');
            el.className = 'w-4 h-4 bg-blue-500 border-2 border-white rounded-full shadow-[0_0_10px_rgba(59,130,246,0.8)]';
            userMarkerRef.current = new maplibregl.Marker({ element: el })
              .setLngLat([loc.longitude, loc.latitude])
              .addTo(mapRef.current);
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

  return (
    <div className="relative w-full h-full flex flex-col">
      {geoError && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-gray-900 bg-opacity-80 text-white px-4 py-2 rounded-full text-sm shadow-md pointer-events-none transition-opacity">
          {geoError}
        </div>
      )}
      
      <div ref={mapContainerRef} className="flex-1 w-full" />
      
      <MapControls onRecenter={handleRecenter} locating={locating} />
    </div>
  );
};
