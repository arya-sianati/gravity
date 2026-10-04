import React, { useEffect, useState } from 'react';
import { useActiveSession } from '../context/ActiveSessionContext';

export const ActiveActivityScreen: React.FC = () => {
  const { activeSession, leaveActiveSession } = useActiveSession();
  const [elapsed, setElapsed] = useState<string>('00:00:00');
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (!activeSession) return;

    const startedAt = new Date(activeSession.started_at).getTime();

    const updateTimer = () => {
      const now = Date.now();
      const diff = Math.max(0, Math.floor((now - startedAt) / 1000));
      const h = Math.floor(diff / 3600).toString().padStart(2, '0');
      const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
      const s = (diff % 60).toString().padStart(2, '0');
      setElapsed(`${h}:${m}:${s}`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [activeSession]);

  if (!activeSession) {
    return null; // Should ideally be handled by routing, but safe fallback
  }

  const handleLeave = async () => {
    setLeaving(true);
    try {
      await leaveActiveSession();
    } catch (err) {
      alert('Failed to leave session');
      setLeaving(false);
    }
  };

  return (
    <div className="flex-1 bg-gray-900 p-6 flex flex-col items-center justify-center relative overflow-y-auto">
      <div className="absolute top-6 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest shadow-[0_0_10px_rgba(220,38,38,0.8)] animate-pulse">
        LIVE
      </div>
      
      <div className="w-24 h-24 bg-gray-800 rounded-full flex items-center justify-center text-5xl shadow-xl mb-4 border border-gray-700" style={{ borderColor: activeSession.activity_type_details.color }}>
        {activeSession.activity_type_details.icon}
      </div>
      
      <h1 className="text-3xl font-bold text-white mb-2 text-center">
        {activeSession.activity_type_details.name}
      </h1>
      
      {activeSession.label && (
        <span className="bg-gray-800 text-gray-300 px-3 py-1 rounded-full text-sm mb-6 border border-gray-700">
          {activeSession.label}
        </span>
      )}

      <div className="text-6xl font-mono text-white mb-8 tracking-tighter">
        {elapsed}
      </div>

      <div className="bg-gray-800 rounded-xl p-4 w-full max-w-sm mb-8 border border-gray-700 flex flex-col gap-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-400">Status</span>
          <span className="text-white capitalize">{activeSession.status}</span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-400">Active Participants</span>
          <span className="text-white font-medium">{activeSession.active_participants_count}</span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-400">Created By</span>
          <span className="text-white">{activeSession.created_by.display_name || activeSession.created_by.username}</span>
        </div>
      </div>

      <button
        onClick={handleLeave}
        disabled={leaving}
        className="w-full max-w-sm bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-6 rounded-xl transition-colors shadow-lg shadow-red-600/20 active:scale-[0.98] disabled:opacity-50"
      >
        {leaving ? 'Leaving...' : 'Finish / Leave'}
      </button>
    </div>
  );
};
