import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router';
import { getActivities } from '../api/activities';
import type { ActivityType } from '../api/activities';
import { startSession, getNearbySessions, joinSession } from '../api/sessions';
import type { NearbySession } from '../api/sessions';
import { requestCurrentLocation } from '../lib/map/geolocation';
import { useActiveSession } from '../context/ActiveSessionContext';
import { ActiveActivityScreen } from './ActiveActivityScreen';

export const StartActivityScreen: React.FC = () => {
  const navigate = useNavigate();
  const { activeSession, refreshActiveSession } = useActiveSession();
  const hadActiveSession = useRef(false);

  useEffect(() => {
    if (activeSession) {
      hadActiveSession.current = true;
    } else if (hadActiveSession.current) {
      hadActiveSession.current = false;
      navigate('/', { replace: true });
    }
  }, [activeSession, navigate]);
  
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedActivity, setSelectedActivity] = useState<ActivityType | null>(null);
  const [nearbySessions, setNearbySessions] = useState<NearbySession[]>([]);
  const [checkingNearby, setCheckingNearby] = useState(false);
  const [starting, setStarting] = useState(false);
  
  // For 'Other' label
  const [label, setLabel] = useState('');
  const [showLabelInput, setShowLabelInput] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchActivities = async () => {
      try {
        setLoading(true);
        const data = await getActivities();
        if (mounted) {
          setActivities(data);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) setError(err.message || 'Failed to load activities');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchActivities();
    return () => { mounted = false; };
  }, []);

  if (activeSession) {
    return <ActiveActivityScreen />;
  }

  const handleSelectActivity = (activity: ActivityType) => {
    setSelectedActivity(activity);
    setCheckingNearby(true);
    setError(null);

    requestCurrentLocation(
      async (loc) => {
        try {
          const sessions = await getNearbySessions(activity.slug, loc.latitude, loc.longitude);
          setNearbySessions(sessions);
          if (sessions.length === 0) {
            // No nearby sessions, proceed to start
            proceedToStart(activity, loc.latitude, loc.longitude);
          }
        } catch (err) {
          setError('Failed to check nearby sessions.');
        } finally {
          setCheckingNearby(false);
        }
      },
      (err) => {
        setCheckingNearby(false);
        setError('Location required to start activity. ' + err.message);
      }
    );
  };

  const proceedToStart = (activity: ActivityType, lat: number, lng: number, forceSeparate = false) => {
    if (activity.slug === 'other' && !forceSeparate) {
      // Need label first
      setShowLabelInput(true);
      return;
    }
    executeStart(activity.id, lat, lng, label || undefined);
  };

  const executeStart = async (id: number, lat: number, lng: number, lbl?: string) => {
    setStarting(true);
    try {
      await startSession(id, lat, lng, lbl);
      await refreshActiveSession();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start session');
      setStarting(false);
    }
  };

  const handleJoin = async (sessionId: string) => {
    setStarting(true);
    try {
      await joinSession(sessionId);
      await refreshActiveSession();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to join session');
      setStarting(false);
    }
  };

  const handleLabelSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;
    
    requestCurrentLocation(
      (loc) => { executeStart(selectedActivity!.id, loc.latitude, loc.longitude, label.trim()); },
      (err) => { setError('Location required. ' + err.message); }
    );
  };

  return (
    <div className="flex-1 bg-gray-900 px-6 pb-6 pt-[calc(env(safe-area-inset-top,0px)+1.5rem)] flex flex-col h-full overflow-y-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Start Activity</h1>
      
      {loading && (
        <div className="flex justify-center items-center py-10">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/20 border border-red-500/40 text-red-100 p-4 rounded-xl mb-6 text-sm flex flex-col gap-2">
          <span>{error}</span>
          <div className="flex items-center gap-3">
            {selectedActivity && (
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  proceedToStart(selectedActivity, 40.5985, -75.5085);
                }}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
              >
                Use Campus Location
              </button>
            )}
            <button
              type="button"
              onClick={() => { setError(null); setSelectedActivity(null); setShowLabelInput(false); setCheckingNearby(false); }}
              className="text-gray-400 hover:text-white underline font-semibold text-xs"
            >
              Reset
            </button>
          </div>
        </div>
      )}

      {checkingNearby && (
        <div className="flex flex-col justify-center items-center py-10 text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-4"></div>
          Checking area for active sessions...
        </div>
      )}

      {!checkingNearby && showLabelInput && (
        <form onSubmit={handleLabelSubmit} className="flex flex-col items-center justify-center py-10 w-full max-w-sm mx-auto">
          <label className="text-white mb-2 font-medium">What activity are you doing?</label>
          <input
            type="text"
            maxLength={50}
            required
            value={label}
            onChange={e => setLabel(e.target.value)}
            className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:outline-none focus:border-indigo-500 mb-6"
            placeholder="e.g. Pickleball"
          />
          <button
            type="submit"
            disabled={starting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition-colors shadow-lg disabled:opacity-50"
          >
            {starting ? 'Starting...' : 'Start'}
          </button>
          <button type="button" onClick={() => { setShowLabelInput(false); setSelectedActivity(null); }} className="mt-4 text-gray-400 underline text-sm">Cancel</button>
        </form>
      )}

      {!checkingNearby && !showLabelInput && nearbySessions.length > 0 && selectedActivity && (
        <div className="flex flex-col gap-4 max-w-sm mx-auto w-full">
          <div className="bg-indigo-900/30 border border-indigo-500/50 p-4 rounded-xl text-center mb-4">
            <h2 className="text-white font-bold text-lg mb-1">{selectedActivity.name} is already happening nearby!</h2>
            <p className="text-indigo-200 text-sm">Join an active session or start your own.</p>
          </div>
          
          {nearbySessions.map(session => (
            <div key={session.id} className="bg-gray-800 border border-gray-700 p-4 rounded-xl flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <span className="text-white font-medium">{session.active_participants_count} active participants</span>
                <span className="text-gray-400 text-sm">{Math.round(session.distance_m)}m away</span>
              </div>
              <button
                onClick={() => handleJoin(session.id)}
                disabled={starting}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                Join Session
              </button>
            </div>
          ))}

          <div className="relative flex py-4 items-center">
            <div className="flex-grow border-t border-gray-700"></div>
            <span className="flex-shrink-0 mx-4 text-gray-500 text-sm">or</span>
            <div className="flex-grow border-t border-gray-700"></div>
          </div>

          <button
            onClick={() => requestCurrentLocation(
              (loc) => proceedToStart(selectedActivity, loc.latitude, loc.longitude, true),
              (_err) => setError('Location required.')
            )}
            disabled={starting}
            className="w-full bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {starting ? 'Starting...' : 'Start Separately'}
          </button>
          <button type="button" onClick={() => { setSelectedActivity(null); setNearbySessions([]); }} className="mt-4 text-gray-400 underline text-sm mx-auto">Cancel</button>
        </div>
      )}

      {!loading && !error && !checkingNearby && !showLabelInput && nearbySessions.length === 0 && !selectedActivity && (
        <div className="grid grid-cols-2 gap-4">
          {activities.map(activity => (
            <button
              key={activity.id}
              onClick={() => handleSelectActivity(activity)}
              className="bg-gray-800 hover:bg-gray-700 transition-colors rounded-xl p-4 flex flex-col items-center justify-center border border-gray-700 shadow-sm"
              style={{ borderBottomColor: activity.color, borderBottomWidth: 4 }}
            >
              <div className="text-4xl mb-2">{activity.icon}</div>
              <span className="text-white font-medium">{activity.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
