import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { getActivities } from '../api/activities';
import type { ActivityType } from '../api/activities';

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
}

export const LeaderboardScreen: React.FC = () => {
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [selectedActivity, setSelectedActivity] = useState<string>('');
  const [period, setPeriod] = useState<'today' | 'week' | 'season' | 'all'>('all');
  
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getActivities().then(res => {
      setActivities(res);
      if (res.length > 0) {
        setSelectedActivity(res[0].slug);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedActivity) return;
    setLoading(true);
    setError(null);
    apiClient.get<LeaderboardResponse>(`/api/leaderboards/${selectedActivity}/`, { params: { period } })
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
  }, [selectedActivity, period]);

  return (
    <div className="flex-1 bg-gray-900 flex flex-col items-center p-4">
      <h1 className="text-2xl font-bold text-white mb-6">Leaderboards</h1>
      
      {/* Activity Selector */}
      <div className="w-full max-w-md mb-4">
        <select 
          className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg p-3 outline-none"
          value={selectedActivity}
          onChange={e => setSelectedActivity(e.target.value)}
        >
          {activities.map(act => (
            <option key={act.id} value={act.slug}>{act.icon} {act.name}</option>
          ))}
        </select>
      </div>

      {/* Period Selector */}
      <div className="w-full max-w-md flex bg-gray-800 rounded-lg p-1 mb-6 border border-gray-700">
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

      {/* Leaderboard Content */}
      <div className="w-full max-w-md bg-gray-800 rounded-xl border border-gray-700 overflow-hidden flex-1 flex flex-col">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading...</div>
        ) : error && !data?.rows?.length ? (
          <div className="p-8 text-center text-red-400">{error}</div>
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
                  <span className="text-white font-mono">{Number.isInteger(row.value) ? row.value : Number(row.value).toFixed(2)}</span>
                </div>
              ))}
            </div>
            
            {data.me && (
              <div className="bg-blue-900/40 p-4 border-t border-blue-800 flex justify-between items-center mt-auto">
                <div className="flex items-center gap-4">
                  <span className="font-bold w-6 text-center text-blue-400">{data.me.rank}</span>
                  <span className="text-white font-medium">You</span>
                </div>
                <span className="text-white font-mono">{Number.isInteger(data.me.value) ? data.me.value : Number(data.me.value).toFixed(2)}</span>
              </div>
            )}
          </>
        ) : (
          <div className="p-8 text-center text-gray-400">
            No data available for this period.
          </div>
        )}
      </div>
    </div>
  );
};
