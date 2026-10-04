import React, { useState, useEffect, useCallback } from 'react';
import { getAreaHistory } from '../../api/history';
import type { AreaHistoryResponse } from '../../api/history';

interface AreaHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  lat: number;
  lng: number;
  label?: string;
}

const PERIODS = [
  { id: 'today', label: 'Today' },
  { id: '7d', label: '7D' },
  { id: '30d', label: '30D' },
  { id: '90d', label: '90D' },
  { id: 'all', label: 'All' },
] as const;

const RADII = [
  { value: 250, label: '250m' },
  { value: 500, label: '500m' },
  { value: 1000, label: '1 km' },
  { value: 2000, label: '2 km' },
  { value: 5000, label: '5 km' },
];

export const AreaHistoryModal: React.FC<AreaHistoryModalProps> = ({
  isOpen,
  onClose,
  lat,
  lng,
  label,
}) => {
  const [period, setPeriod] = useState<'today' | '7d' | '30d' | '90d' | 'all'>('30d');
  const [radiusM, setRadiusM] = useState<number>(500);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AreaHistoryResponse | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAreaHistory({
        lat,
        lng,
        radius_m: radiusM,
        period,
      });
      setData(res);
    } catch (err: any) {
      console.error('Failed to load area history', err);
      setError(err.response?.data?.detail || 'Failed to load area history.');
    } finally {
      setLoading(false);
    }
  }, [lat, lng, radiusM, period]);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, fetchHistory]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div
        className="bg-gray-900 border border-gray-800 rounded-3xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden shadow-2xl text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="px-5 py-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/90">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🏛️</span>
              <h2 className="text-lg font-bold text-white tracking-tight">Area Reputation</h2>
            </div>
            <p className="text-xs text-gray-400">
              {label ? label : `${lat.toFixed(4)}, ${lng.toFixed(4)}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-800 hover:bg-gray-700 flex items-center justify-center text-gray-400 hover:text-white transition-colors"
            title="Close"
          >
            ✕
          </button>
        </header>

        {/* Controls: Period & Radius */}
        <div className="px-5 py-3 border-b border-gray-800/80 bg-gray-950/60 flex flex-col gap-2.5">
          {/* Period selector */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Timeframe</span>
            <div className="flex bg-gray-800/90 p-1 rounded-xl gap-1">
              {PERIODS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPeriod(p.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-all ${
                    period === p.id
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Radius selector */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Area Radius</span>
            <div className="flex bg-gray-800/90 p-1 rounded-xl gap-1">
              {RADII.map((r) => (
                <button
                  key={r.value}
                  onClick={() => setRadiusM(r.value)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-all ${
                    radiusM === r.value
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="h-60 flex flex-col items-center justify-center space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <p className="text-xs text-gray-400">Aggregating historical area reputation...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-900/30 border border-red-800/60 rounded-2xl text-center space-y-2">
              <p className="text-sm text-red-300">{error}</p>
              <button
                onClick={fetchHistory}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs rounded-lg text-white"
              >
                Retry
              </button>
            </div>
          ) : data?.privacy_suppressed ? (
            /* Privacy Safeguard Active */
            <div className="p-5 bg-amber-950/30 border border-amber-800/60 rounded-2xl text-center space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-amber-900/40 flex items-center justify-center text-2xl">
                🛡️
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-amber-200">Privacy Safeguard Active</h3>
                <p className="text-xs text-gray-300">
                  {data.message}
                </p>
                <p className="text-[11px] text-gray-400 pt-1">
                  At least {data.min_participants_required} unique participants are required before
                  activity breakdowns and patterns can be publicly displayed.
                </p>
              </div>
            </div>
          ) : data && data.total_participations === 0 ? (
            /* Zero Activity */
            <div className="h-56 flex flex-col items-center justify-center text-center p-6 bg-gray-950/40 rounded-2xl border border-gray-800/60 space-y-3">
              <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-2xl">
                📍
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">Quiet Territory</h3>
                <p className="text-xs text-gray-400 max-w-xs">
                  No completed activities recorded within {radiusM >= 1000 ? `${radiusM / 1000} km` : `${radiusM}m`} for this period.
                </p>
              </div>
            </div>
          ) : data ? (
            <>
              {/* Dominant Activity Banner */}
              {data.dominant_activity && (
                <div
                  className="p-4 rounded-2xl border relative overflow-hidden flex items-center gap-4 shadow-lg"
                  style={{
                    backgroundColor: `${data.dominant_activity.color}15`,
                    borderColor: `${data.dominant_activity.color}40`,
                  }}
                >
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow-inner shrink-0"
                    style={{ backgroundColor: `${data.dominant_activity.color}30` }}
                  >
                    <span>{data.dominant_activity.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-gray-400 block">
                      Dominant Activity
                    </span>
                    <h3 className="text-lg font-black text-white truncate">
                      {data.dominant_activity.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-300">
                      <span className="font-bold text-white">
                        {data.dominant_activity.share_percentage}%
                      </span>
                      <span>share</span>
                      <span>•</span>
                      <span>{data.dominant_activity.participation_count} participations</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="bg-gray-950/60 border border-gray-800/80 p-3 rounded-2xl">
                  <span className="text-[11px] text-gray-400 block font-medium">Total Sessions</span>
                  <span className="text-xl font-bold text-white">{data.total_sessions}</span>
                </div>
                <div className="bg-gray-950/60 border border-gray-800/80 p-3 rounded-2xl">
                  <span className="text-[11px] text-gray-400 block font-medium">Participants</span>
                  <span className="text-xl font-bold text-white">
                    {data.total_unique_participants}
                  </span>
                </div>
                <div className="bg-gray-950/60 border border-gray-800/80 p-3 rounded-2xl">
                  <span className="text-[11px] text-gray-400 block font-medium">Peak Time</span>
                  <span className="text-sm font-bold text-emerald-400 truncate block">
                    {data.peak_time || 'N/A'}
                  </span>
                </div>
                <div className="bg-gray-950/60 border border-gray-800/80 p-3 rounded-2xl">
                  <span className="text-[11px] text-gray-400 block font-medium">Busiest Day</span>
                  <span className="text-sm font-bold text-blue-400 truncate block">
                    {data.busiest_day || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Activity Breakdown List */}
              <div className="bg-gray-950/60 border border-gray-800/80 rounded-2xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                  Activity Breakdown
                </h4>
                <div className="space-y-3">
                  {data.activities.map((act) => (
                    <div key={act.activity_type_id} className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2 font-semibold text-white">
                          <span>{act.icon}</span>
                          <span>{act.name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-400">
                          <span className="font-bold text-white">{act.share_percentage}%</span>
                          <span>({act.participation_count} visits)</span>
                        </div>
                      </div>
                      {/* Share progress bar */}
                      <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.max(act.share_percentage, 4)}%`,
                            backgroundColor: act.color || '#3B82F6',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Time of Day Distribution */}
              {data.time_distribution.some((b) => b.participation_count > 0) && (
                <div className="bg-gray-950/60 border border-gray-800/80 rounded-2xl p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                      Time of Day
                    </h4>
                    {data.peak_time && (
                      <span className="text-[11px] text-emerald-400 font-medium">
                        Peak: {data.peak_time}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-4 gap-2 pt-1">
                    {data.time_distribution.map((b) => {
                      const isPeak = b.label === data.peak_time && b.participation_count > 0;
                      return (
                        <div
                          key={b.label}
                          className={`p-2 rounded-xl border text-center transition-all ${
                            isPeak
                              ? 'bg-emerald-950/40 border-emerald-600/80 text-white'
                              : 'bg-gray-900/60 border-gray-800 text-gray-400'
                          }`}
                        >
                          <span className="text-[10px] block leading-tight truncate">{b.label}</span>
                          <span className={`text-xs font-bold block mt-1 ${isPeak ? 'text-emerald-400' : 'text-gray-300'}`}>
                            {b.participation_count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Weekday Distribution */}
              {data.weekday_distribution.some((d) => d.participation_count > 0) && (
                <div className="bg-gray-950/60 border border-gray-800/80 rounded-2xl p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                      Weekly Activity
                    </h4>
                    {data.busiest_day && (
                      <span className="text-[11px] text-blue-400 font-medium">
                        Busiest: {data.busiest_day}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-7 gap-1.5 pt-1">
                    {data.weekday_distribution.map((d) => {
                      const isBusiest = d.day === data.busiest_day && d.participation_count > 0;
                      return (
                        <div
                          key={d.day}
                          className={`p-1.5 rounded-xl border text-center ${
                            isBusiest
                              ? 'bg-blue-950/40 border-blue-600/80 text-white'
                              : 'bg-gray-900/60 border-gray-800 text-gray-400'
                          }`}
                        >
                          <span className="text-[10px] block font-medium">
                            {d.day.substring(0, 3)}
                          </span>
                          <span className={`text-xs font-bold block mt-0.5 ${isBusiest ? 'text-blue-400' : 'text-gray-300'}`}>
                            {d.participation_count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
