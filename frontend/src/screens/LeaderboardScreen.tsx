import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { getActivities } from '../api/activities';
import type { ActivityType } from '../api/activities';
import { getSeasons } from '../api/seasons';
import type { Season } from '../api/seasons';

interface LeaderboardRow {
  rank: number;
  user: {
    id: number;
    display_name: string;
  };
  value: number;
}

interface LeaderboardResponse {
  activity: {
    slug: string;
    name: string;
    icon: string;
  };
  metric: {
    slug: string;
    name: string;
    unit: string;
  };
  period: string;
  rows: LeaderboardRow[];
  me: LeaderboardRow | null;
  detail?: string;
  season?: {
    name: string;
    slug: string;
    status: string;
    finalized: boolean;
  };
}

export const LeaderboardScreen: React.FC = () => {
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [selectedActivity, setSelectedActivity] = useState<string>('');
  const [period, setPeriod] = useState<'today' | 'week' | 'season' | 'all'>('all');
  const [selectedSeason, setSelectedSeason] = useState<string>('');
  
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getActivities(), getSeasons()]).then(([acts, seas]) => {
      setActivities(acts);
      if (acts.length > 0) {
        setSelectedActivity(acts[0].slug);
      }
      setSeasons(seas);
      const activeOrCurrent = seas.find(s => s.status === 'live' || s.status === 'upcoming') || seas[0];
      if (activeOrCurrent) {
        setSelectedSeason(activeOrCurrent.slug);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedActivity) return;
    setLoading(true);
    setError(null);
    
    const params: any = { period };
    if (period === 'season' && selectedSeason) {
      params.season = selectedSeason;
    }
    
    apiClient.get<LeaderboardResponse>(`/api/leaderboards/${selectedActivity}/`, { params })
      .then(res => {
        setData(res.data);
        if (res.data.detail) {
           setError(res.data.detail);
        }
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Failed to load leaderboard.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedActivity, period, selectedSeason]);

  return (
    <div className="flex-1 bg-gray-900 flex flex-col items-center p-4">
      <h1 className="text-2xl font-bold text-white mb-6">Leaderboards</h1>
      
      {/* Activity Selector */}
      <div className="w-full max-w-md mb-4 flex gap-2">
        <select 
          className="flex-1 bg-gray-800 text-white border border-gray-700 rounded-lg p-3 outline-none"
          value={selectedActivity}
          onChange={e => setSelectedActivity(e.target.value)}
        >
          {activities.map(act => (
            <option key={act.id} value={act.slug}>{act.icon} {act.name}</option>
          ))}
        </select>
      </div>

      {/* Period Selector */}
      <div className="w-full max-w-md flex bg-gray-800 rounded-lg p-1 mb-4 border border-gray-700">
        {(['today', 'week', 'season', 'all'] as const).map(p => (
          <button
            key={p}
            className={`flex-1 py-2 text-sm font-medium rounded-md capitalize transition-colors ${period === p ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            onClick={() => setPeriod(p)}
          >
            {p}
          </button>
        ))}
      </div>
      
      {/* Season Selector */}
      {period === 'season' && seasons.length > 0 && (
        <div className="w-full max-w-md mb-6">
          <select 
            className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg p-2 text-sm outline-none"
            value={selectedSeason}
            onChange={e => setSelectedSeason(e.target.value)}
          >
            {seasons.map(s => (
              <option key={s.id} value={s.slug}>
                {s.name} {s.status === 'live' ? '(Live)' : s.status === 'ended' ? '(Ended)' : ''} {s.finalized_at ? '(Final)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Leaderboard Content */}
      <div className="w-full max-w-md bg-gray-800 rounded-xl border border-gray-700 overflow-hidden flex-1 flex flex-col mb-16">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading...</div>
        ) : error && !data?.rows?.length ? (
          <div className="p-8 text-center text-red-400">
            {error}
            {period === 'season' && <div className="mt-2 text-sm text-gray-500">No active season available.</div>}
          </div>
        ) : data && data.rows && data.rows.length > 0 ? (
          <>
            <div className="bg-gray-750 p-3 border-b border-gray-700 flex justify-between text-xs font-bold text-gray-400 uppercase tracking-wider">
              <span>Rank & User</span>
              <span>{data.metric.name} {data.metric.unit && `(${data.metric.unit})`}</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {data.rows.map((row) => (
                <div key={row.user.id} className="flex justify-between items-center p-4 border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                  <div className="flex items-center gap-4">
                    <span className={`font-bold w-6 text-center ${row.rank <= 3 ? 'text-yellow-400' : 'text-gray-400'}`}>
                      {row.rank}
                    </span>
                    <span className="text-white font-medium">{row.user.display_name}</span>
                  </div>
                  <span className="text-blue-400 font-bold">{row.value}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="p-8 text-center text-gray-500">No data available for this period.</div>
        )}
      </div>
    </div>
  );
};
