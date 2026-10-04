import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import { requestCurrentLocation, formatGeolocationErrorMessage } from '../../lib/map/geolocation';
import { getActivities } from '../../api/activities';
import type { ActivityType } from '../../api/activities';
import { getLiveMap } from '../../api/map';
import type { LiveMapFeatureCollection } from '../../api/map';
import { getPulseSoon } from '../../api/pulse';
import type { PulseSoonItem } from '../../api/pulse';
import { MapControls } from './MapControls';
import { useGravitySocket } from '../../lib/realtime/useGravitySocket';
import { AreaHistoryModal } from '../history/AreaHistoryModal';

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL || 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';
const FALLBACK_CENTER: [number, number] = [-75.5085, 40.5985]; // Muhlenberg College campus

// Persistent coordinates across tab switching
let cachedCenter: [number, number] | null = null;
let cachedZoom: number | null = null;

const OSM_RASTER_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'osm-tiles': {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors'
    }
  },
  layers: [
    {
      id: 'osm-tiles-layer',
      type: 'raster',
      source: 'osm-tiles',
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

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

  // Pulse Soon Forecasting Overlay
  const [showSoon, setShowSoon] = useState<boolean>(true);
  const [soonItems, setSoonItems] = useState<PulseSoonItem[]>([]);

  // Area History Inspection
  const [historyCoords, setHistoryCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [historyModalOpen, setHistoryModalOpen] = useState<boolean>(false);

  // Realtime
  const { lastMessage } = useGravitySocket('/ws/gravity/');
  const [lastBboxFetchTs, setLastBboxFetchTs] = useState(Date.now());

  useEffect(() => {
    if (lastMessage?.type === 'map.changed' || lastMessage?.type === 'map_changed') {
      setLastBboxFetchTs(Date.now());
    }
  }, [lastMessage]);

  const handleRecenter = useCallback(() => {
    setLocating(true);
    setGeoError(null);
    requestCurrentLocation(
      (loc) => {
        setLocating(false);
        if (mapRef.current) {
          cachedCenter = [loc.longitude, loc.latitude];
          cachedZoom = 14;
          // Jump immediately without camera flight animation
          mapRef.current.jumpTo({ center: [loc.longitude, loc.latitude], zoom: 14 });
          mapRef.current.triggerRepaint();

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
        setGeoError(formatGeolocationErrorMessage(err));
      }
    );
  }, []);

  useEffect(() => {
    let map: maplibregl.Map | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let disposed = false;
    let t1: ReturnType<typeof setTimeout>;
    let t2: ReturnType<typeof setTimeout>;
    let t3: ReturnType<typeof setTimeout>;

    const refreshMap = () => {
      if (map && !disposed) {
        map.resize();
        map.triggerRepaint();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshMap();
      }
    };

    const initMap = () => {
      if (disposed || !mapContainerRef.current) return;
      const rect = mapContainerRef.current.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        requestAnimationFrame(initMap);
        return;
      }

      const initialCenter = cachedCenter || FALLBACK_CENTER;
      const initialZoom = cachedZoom ?? 14;

      map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: STYLE_URL,
        center: initialCenter,
        zoom: initialZoom,
        interactive: true,
        fadeDuration: 0,
        trackResize: true
      });
      mapRef.current = map;

      refreshMap();
      requestAnimationFrame(refreshMap);
      t1 = setTimeout(refreshMap, 60);
      t2 = setTimeout(refreshMap, 250);
      t3 = setTimeout(refreshMap, 600);

      map.on('style.load', refreshMap);
      map.on('data', (e: any) => {
        if (e?.dataType === 'source' && e?.isSourceLoaded) {
          refreshMap();
        }
      });
      map.once('idle', refreshMap);

      // Fallback to OSM raster style if vector style encounters fatal errors
      map.on('error', (e: any) => {
        if (e?.error?.message?.includes('style') || e?.error?.message?.includes('source')) {
          console.warn('MapLibre style error, switching to fallback OSM raster style:', e);
          try {
            map?.setStyle(OSM_RASTER_STYLE);
          } catch (fallbackErr) {
            console.error('OSM raster fallback failed:', fallbackErr);
          }
        }
      });

      // ResizeObserver ensures canvas always fills container immediately upon mount or resize
      resizeObserver = new ResizeObserver(() => {
        refreshMap();
      });
      if (mapContainerRef.current) {
        resizeObserver.observe(mapContainerRef.current);
      }

      window.addEventListener('resize', refreshMap);
      window.addEventListener('pageshow', refreshMap);
      document.addEventListener('visibilitychange', handleVisibilityChange);

      map.on('load', () => {
        refreshMap();
        if (!mapRef.current) return;

        // 1. Setup Pulse Soon Source & Layers (Translucent + Patterned/Dashed Outline)
        if (!mapRef.current.getSource('pulse-soon-source')) {
          mapRef.current.addSource('pulse-soon-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
          });

          // Translucent polygon fill
          mapRef.current.addLayer({
            id: 'pulse-soon-fill',
            type: 'fill',
            source: 'pulse-soon-source',
            paint: {
              'fill-color': ['get', 'color'],
              'fill-opacity': 0.22,
            }
          });

          // Dashed/hatched patterned outline
          mapRef.current.addLayer({
            id: 'pulse-soon-outline',
            type: 'line',
            source: 'pulse-soon-source',
            paint: {
              'line-color': ['get', 'color'],
              'line-width': 2.5,
              'line-dasharray': [3, 2],
              'line-opacity': 0.85,
            }
          });

          // Interactive popup on clicking forecasted region
          mapRef.current.on('click', 'pulse-soon-fill', (e) => {
            if (!e.features || e.features.length === 0) return;
            const props = e.features[0].properties;
            if (!props) return;

            new maplibregl.Popup({ closeButton: true, className: 'gravity-soon-popup' })
              .setLngLat(e.lngLat)
              .setHTML(`
                <div style="font-family: sans-serif; color: #111; padding: 4px; min-width: 180px;">
                  <div style="display: flex; align-items: center; gap: 6px; font-weight: bold; font-size: 13px;">
                    <span>${props.icon || '🔮'}</span>
                    <span>${props.name} (Soon)</span>
                  </div>
                  <div style="font-size: 11px; color: #4338ca; font-weight: 600; margin-top: 4px;">
                    🕒 ${props.window}
                  </div>
                  <div style="font-size: 11px; color: #047857; margin-top: 2px;">
                    ⭐ ${props.confidence}
                  </div>
                  <div style="font-size: 11px; color: #4b5563; margin-top: 4px;">
                    ${props.reason}
                  </div>
                </div>
              `)
              .addTo(mapRef.current!);
          });

          mapRef.current.on('mouseenter', 'pulse-soon-fill', () => {
            if (mapRef.current) mapRef.current.getCanvas().style.cursor = 'pointer';
          });

          mapRef.current.on('mouseleave', 'pulse-soon-fill', () => {
            if (mapRef.current) mapRef.current.getCanvas().style.cursor = '';
          });
        }

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
          refreshMap();
        }).catch(err => console.error("Failed to load activities for map prep", err));

        if (mapRef.current) {
          const bounds = mapRef.current.getBounds();
          setBbox([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
        }
        if (!cachedCenter) {
          handleRecenter();
        }
      });

      let timeout: ReturnType<typeof setTimeout>;
      map.on('moveend', () => {
        if (!map || disposed) return;
        const c = map.getCenter();
        cachedCenter = [c.lng, c.lat];
        cachedZoom = map.getZoom();

        clearTimeout(timeout);
        timeout = setTimeout(() => {
          if (!map || disposed) return;
          const bounds = map.getBounds();
          setBbox([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
        }, 500);
      });

    };

    // Request animation frame before initializing to allow flex/grid layout computation
    requestAnimationFrame(initMap);

    return () => {
      disposed = true;
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      window.removeEventListener('resize', refreshMap);
      window.removeEventListener('pageshow', refreshMap);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (resizeObserver) resizeObserver.disconnect();
      if (map) {
        try {
          const c = map.getCenter();
          cachedCenter = [c.lng, c.lat];
          cachedZoom = map.getZoom();
        } catch {}
        map.remove();
      }
      mapRef.current = null;
    };
  }, [handleRecenter]);

  useEffect(() => {
    if (!bbox || activities.length === 0) return;

    const fetchMapData = async () => {
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
        mapRef.current?.triggerRepaint();
      } catch (err) {
        console.error("Failed to fetch live heat map", err);
      }

      // Fetch Pulse Soon forecasts around current viewport center
      try {
        if (mapRef.current) {
          const center = mapRef.current.getCenter();
          const soonData = await getPulseSoon({
            lat: center.lat,
            lng: center.lng,
            radius: 12000,
          });
          setSoonItems(soonData.items);
        }
      } catch (err) {
        console.error("Failed to fetch pulse soon forecasts", err);
      }
    };

    fetchMapData();
    const interval = setInterval(fetchMapData, 30000);
    return () => clearInterval(interval);
  }, [bbox, activities, hiddenActivities, lastBboxFetchTs]);

  // Synchronize Pulse Soon GeoJSON source
  useEffect(() => {
    const source = mapRef.current?.getSource('pulse-soon-source') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!showSoon) {
      source.setData({ type: 'FeatureCollection', features: [] });
      mapRef.current?.triggerRepaint();
      return;
    }

    const features = soonItems
      .filter((item) => !hiddenActivities.has(item.activity.slug))
      .map((item) => ({
        type: 'Feature' as const,
        geometry: item.geometry,
        properties: {
          name: item.activity.name,
          slug: item.activity.slug,
          icon: item.activity.icon,
          color: item.activity.color || '#6366f1',
          window: item.expected_window.display,
          confidence: item.confidence_display,
          reason: item.reason,
        },
      }));

    source.setData({
      type: 'FeatureCollection',
      features,
    });
    mapRef.current?.triggerRepaint();
  }, [soonItems, showSoon, hiddenActivities]);

  const toggleActivityFilter = (slug: string) => {
    setHiddenActivities(prev => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  return (
    <div className="relative w-full h-full overflow-hidden">
      {geoError && (
        <div className="absolute top-[calc(env(safe-area-inset-top,0px)+0.75rem)] left-1/2 transform -translate-x-1/2 z-20 bg-gray-900 bg-opacity-80 text-white px-4 py-2 rounded-full text-sm shadow-md pointer-events-none transition-opacity">
          {geoError}
        </div>
      )}
      
      {/* Filters Overlay */}
      <div className="absolute top-[calc(env(safe-area-inset-top,0px)+0.75rem)] right-4 z-20 flex flex-wrap gap-2 justify-end max-w-[70%]">
        {/* Pulse Soon Toggle Pill */}
        <button
          onClick={() => setShowSoon(!showSoon)}
          className={`px-3 py-1.5 rounded-full text-xs font-bold border shadow-sm transition-all flex items-center gap-1.5 cursor-pointer ${
            showSoon
              ? 'bg-indigo-600 border-indigo-400 text-white shadow-indigo-600/30'
              : 'bg-gray-800 border-gray-700 text-gray-500 opacity-70'
          }`}
          title="Toggle forecasted recurring activity patterns"
        >
          <span>🔮</span>
          <span>Forecasts {showSoon ? 'ON' : 'OFF'}</span>
        </button>
        {activities.map(act => {
          const isHidden = hiddenActivities.has(act.slug);
          return (
            <button
              key={act.slug}
              onClick={() => toggleActivityFilter(act.slug)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border shadow-sm transition-colors cursor-pointer ${
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

      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />
      <MapControls
        onRecenter={handleRecenter}
        locating={locating}
        onOpenHistory={() => {
          if (mapRef.current) {
            const center = mapRef.current.getCenter();
            setHistoryCoords({ lat: center.lat, lng: center.lng });
            setHistoryModalOpen(true);
          }
        }}
      />

      {historyCoords && (
        <AreaHistoryModal
          isOpen={historyModalOpen}
          onClose={() => setHistoryModalOpen(false)}
          lat={historyCoords.lat}
          lng={historyCoords.lng}
        />
      )}
    </div>
  );
};
