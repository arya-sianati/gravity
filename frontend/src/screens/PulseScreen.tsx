import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getActivities } from '../api/activities';
import type { ActivityType } from '../api/activities';
import { getPulseNow } from '../api/pulse';
import type { PulseItem } from '../api/pulse';
import { joinSession } from '../api/sessions';
import { requestCurrentLocation } from '../lib/map/geolocation';
import { useGravitySocket } from '../lib/realtime/useGravitySocket';
import { useActiveSession } from '../context/ActiveSessionContext';

export const PulseScreen: React.FC = () => {
  const navigate = useNavigate();
  const { activeSession, refreshActiveSession } = useActiveSession();

  // Location state
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = useState<boolean>(true);
  const [locationError, setLocationError] = useState<string | null>(null);

  // Activities filter
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [selectedActivity, setSelectedActivity] = useState<string>('all');

  // Pulse feed state
  const [items, setItems] = useState<PulseItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [feedError, setFeedError] = useState<string | null>(null);
  const [joiningId, setJoiningId] = useState<string | null>(null);
  const [joinError, setJoinError] = useState<string | null>(null);

  // Realtime updates
  const { lastMessage } = useGravitySocket('/ws/gravity/');

  // Location request helper
  const acquireLocation = useCallback(() => {
    setLocating(true);
    setLocationError(null);

    requestCurrentLocation(
      (loc) => {
        setCoords({ lat: loc.latitude, lng: loc.longitude });
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        let msg = 'Unable to determine your location.';
        if (err.code === 1) {
          msg = 'Location permission was denied. Please enable location to discover activity around you.';
        } else if (err.code === 2) {
          msg = 'Location is currently unavailable.';
        } else if (err.code === 3) {
          msg = 'Location request timed out. Please try again.';
        }
        setLocationError(msg);
      }
    );
  }, []);

  // On mount: fetch activities & request location
  useEffect(() => {
    getActivities()
      .then((res) => setActivities(res))
      .catch((err) => console.error('Failed to load activities', err));

    acquireLocation();
  }, [acquireLocation]);

  // Fetch Pulse items
  const fetchPulseFeed = useCallback(async (isBackground = false) => {
    if (!coords) return;
    if (!isBackground) setLoading(true);
    setFeedError(null);

    try {
      const data = await getPulseNow({
        lat: coords.lat,
        lng: coords.lng,
        activity: selectedActivity === 'all' ? undefined : selectedActivity,
      });
      setItems(data.items);
    } catch (err: any) {
      console.error('Pulse feed error', err);
      if (!isBackground) {
        setFeedError(err.response?.data?.detail || 'Failed to load pulse feed.');
      }
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, [coords, selectedActivity]);

  // Refetch when coords or selected activity changes
  useEffect(() => {
    if (coords) {
      fetchPulseFeed();
    }
  }, [coords, selectedActivity, fetchPulseFeed]);

  // Realtime refetch on map_changed
  useEffect(() => {
    if (lastMessage?.type === 'map.changed' || lastMessage?.type === 'map_changed') {
      fetchPulseFeed(true);
    }
  }, [lastMessage, fetchPulseFeed]);

  // Background refetch on visibilitychange & periodic reconciliation polling
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && coords) {
        fetchPulseFeed(true);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    const interval = setInterval(() => {
      if (coords) fetchPulseFeed(true);
    }, 20000);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(interval);
    };
  }, [coords, fetchPulseFeed]);

  // Handle Join
  const handleJoin = async (sessionId: string) => {
    setJoiningId(sessionId);
    setJoinError(null);

    try {
      await joinSession(sessionId, { source: 'pulse' });
      await refreshActiveSession();
      navigate('/start');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to join session.';
      setJoinError(msg);
      setTimeout(() => setJoinError(null), 4000);
    } finally {
      setJoiningId(null);
    }
  };

  // Format recency helper
  const formatRecency = (isoDate: string) => {
    const diffSeconds = Math.max(0, (Date.now() - new Date(isoDate).getTime()) / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 1) return 'Just started';
    if (diffMinutes < 60) return `Started ${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    return `Started ${diffHours}h ago`;
  };

  return (
    <div className="flex-1 bg-gray-950 flex flex-col h-full overflow-hidden text-white">
      {/* Header */}
      <header className="p-4 bg-gray-900/90 border-b border-gray-800 flex justify-between items-center backdrop-blur-sm z-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <h1 className="text-xl font-bold tracking-tight">Pulse</h1>
          </div>
          <p className="text-xs text-gray-400">What's happening around you right now</p>
        </div>

        {coords && (
          <button
            onClick={() => fetchPulseFeed()}
            disabled={loading}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-full transition-colors active:scale-95"
            title="Refresh feed"
            aria-label="Refresh feed"
          >
            <svg
              className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
      </header>

      {/* Join Toast Error */}
      {joinError && (
        <div className="bg-red-900/90 border-b border-red-700 px-4 py-2 text-xs text-center text-red-200 animate-fade-in">
          {joinError}
        </div>
      )}

      {/* Activity Filter Chips */}
      <div className="px-4 py-2.5 bg-gray-900/50 border-b border-gray-800/80 overflow-x-auto no-scrollbar flex gap-2">
        <button
          onClick={() => setSelectedActivity('all')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
            selectedActivity === 'all'
              ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]'
              : 'bg-gray-800/80 text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          All Activity
        </button>
        {activities.map((act) => (
          <button
            key={act.id}
            onClick={() => setSelectedActivity(act.slug)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap flex items-center gap-1.5 transition-all ${
              selectedActivity === act.slug
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]'
                : 'bg-gray-800/80 text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <span>{act.icon}</span>
            <span>{act.name}</span>
          </button>
        ))}
      </div>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {locating ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="text-sm text-gray-400">Locating nearby activities...</p>
          </div>
        ) : locationError ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-gray-900/40 rounded-2xl border border-gray-800 space-y-4">
            <div className="w-12 h-12 rounded-full bg-blue-900/30 flex items-center justify-center text-2xl">
              📍
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-white">Location Access Needed</h2>
              <p className="text-xs text-gray-400 max-w-xs">{locationError}</p>
            </div>
            <button
              onClick={acquireLocation}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-md transition-all active:scale-95"
            >
              Enable Location & Retry
            </button>
          </div>
        ) : loading && items.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="text-sm text-gray-400">Scanning Gravity network...</p>
          </div>
        ) : feedError ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-gray-900/40 rounded-2xl border border-gray-800 space-y-3">
            <p className="text-sm text-red-400">{feedError}</p>
            <button
              onClick={() => fetchPulseFeed()}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-xs font-medium rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-gray-900/30 rounded-2xl border border-gray-800/80 space-y-4">
            <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-2xl">
              📡
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-white">It's quiet around here right now.</h2>
              <p className="text-xs text-gray-400 max-w-xs">
                {selectedActivity !== 'all'
                  ? `No live ${activities.find((a) => a.slug === selectedActivity)?.name || 'activity'} nearby.`
                  : 'Be the first to create gravity by starting an activity!'}
              </p>
            </div>
            <button
              onClick={() => navigate('/start')}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-indigo-600/30 transition-all active:scale-95"
            >
              + Start an Activity
            </button>
          </div>
        ) : (
          items.map((item) => {
            const displayName =
              item.activity.slug === 'other' && item.label
                ? item.label
                : item.activity.name;

            const isCurrentSession = activeSession?.id === item.session_id;

            return (
              <div
                key={item.session_id}
                className="bg-gray-900/80 rounded-2xl border border-gray-800 hover:border-gray-700/80 transition-all p-4 shadow-sm flex flex-col gap-3 relative overflow-hidden"
              >
                {/* Event multiplier badge */}
                {item.event && (
                  <div className="absolute top-0 right-0 bg-gradient-to-l from-amber-500 to-yellow-500 text-black font-extrabold text-[10px] px-3 py-0.5 rounded-bl-xl shadow-md uppercase tracking-wider flex items-center gap-1">
                    <span>⚡</span>
                    <span>{item.event.xp_multiplier > 1.0 ? `${item.event.xp_multiplier}× XP Event` : item.event.name}</span>
                  </div>
                )}

                {/* Card Top: Icon, Title, Activity, Meta */}
                <div className="flex items-start gap-3">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-inner shrink-0"
                    style={{ backgroundColor: `${item.activity.color || '#3B82F6'}20` }}
                  >
                    <span>{item.activity.icon}</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="font-bold text-white text-base truncate">
                        {displayName}
                      </h2>
                    </div>

                    <div className="flex flex-wrap items-center gap-y-1 gap-x-2.5 text-xs text-gray-400 mt-1">
                      <span className="flex items-center gap-1 text-emerald-400 font-medium">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        {item.participant_count} active
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1 text-blue-400">
                        <span>📍</span>
                        {item.distance.display}
                      </span>
                      <span>•</span>
                      <span className="text-gray-400">{formatRecency(item.started_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Card Bottom: Join & View on Map Buttons */}
                <div className="flex items-center gap-2 pt-1 border-t border-gray-800/60">
                  <button
                    onClick={() => handleJoin(item.session_id)}
                    disabled={isCurrentSession || !item.can_join || joiningId === item.session_id}
                    className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                      isCurrentSession
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60 cursor-default'
                        : !item.can_join
                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                        : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 active:scale-95'
                    }`}
                  >
                    {joiningId === item.session_id ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : isCurrentSession ? (
                      <>
                        <span>✓</span>
                        <span>Active Here</span>
                      </>
                    ) : !item.can_join ? (
                      <span>In Another Session</span>
                    ) : (
                      <>
                        <span>Join</span>
                        <span className="text-indigo-300">→</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => navigate('/')}
                    className="py-2 px-3.5 bg-gray-800 hover:bg-gray-700/80 text-gray-300 hover:text-white rounded-xl text-xs font-medium border border-gray-700/60 transition-all flex items-center gap-1 active:scale-95"
                    title="View on Live Map"
                  >
                    <span>🗺️</span>
                    <span>Map</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
