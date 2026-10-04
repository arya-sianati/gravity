import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router';
import { useActiveSession } from '../context/ActiveSessionContext';
import { QRCodeSVG } from 'qrcode.react';
import { getJoinCode } from '../api/sessions';
import { MetricEntryForm } from '../components/MetricEntryForm';
import type { MetricEntryFormHandle } from '../components/MetricEntryForm';

export const ActiveActivityScreen: React.FC = () => {
  const navigate = useNavigate();
  const { activeSession, leaveActiveSession, graceWarning } = useActiveSession();
  const [elapsed, setElapsed] = useState<string>('00:00:00');
  const [leaving, setLeaving] = useState(false);
  const [showQR, setShowQR] = useState(false);
  const [joinUrl, setJoinUrl] = useState<string | null>(null);
  const [loadingQR, setLoadingQR] = useState(false);
  const formRef = useRef<MetricEntryFormHandle>(null);

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

  const handleShowQR = async () => {
    if (!activeSession) return;
    if (!joinUrl) {
      setLoadingQR(true);
      setShowQR(true);
      try {
        const data = await getJoinCode(activeSession.id);
        setJoinUrl(data.join_url);
      } catch (err: any) {
        console.error('Failed to get join QR:', err);
        const msg = err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Unknown error';
        alert(`Failed to get join QR: ${msg}`);
        setShowQR(false);
      } finally {
        setLoadingQR(false);
      }
    } else {
      setShowQR(true);
    }
  };

  if (!activeSession) {
    return null; // Should ideally be handled by routing, but safe fallback
  }

  const handleLeave = async () => {
    if (formRef.current) {
      const ok = await formRef.current.submit();
      if (!ok) return;
    }
    
    setLeaving(true);
    try {
      await leaveActiveSession();
      navigate('/', { replace: true });
    } catch (err) {
      alert('Failed to leave session');
      setLeaving(false);
    }
  };

  const [copied, setCopied] = useState(false);

  const handleCopyLink = () => {
    if (!joinUrl) return;
    navigator.clipboard.writeText(joinUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  return (
    <div className="flex-1 bg-gray-900 p-6 flex flex-col items-center justify-center relative overflow-y-auto">
      <div className="absolute top-6 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest shadow-[0_0_10px_rgba(220,38,38,0.8)] animate-pulse">
        LIVE
      </div>

      {/* Grace Warning Banner (Phase 18 Requirement 21) */}
      {graceWarning && (
        <div className="w-full max-w-sm mb-4 bg-amber-500/20 border border-amber-500/50 rounded-xl p-3 flex items-center space-x-2 text-amber-200 text-xs shadow-lg animate-pulse">
          <span className="text-base">⚠️</span>
          <span>
            You moved away from this activity area. Return within{' '}
            <strong className="font-bold text-amber-100">{graceWarning.remainingSeconds}s</strong> to keep the activity active.
          </span>
        </div>
      )}
      
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

      <div className="text-6xl font-mono text-white mb-6 tracking-tighter">
        {elapsed}
      </div>

      {activeSession.my_participation && (
        <MetricEntryForm 
          ref={formRef}
          participationId={activeSession.my_participation.id}
          metricsDef={activeSession.activity_type_details.metrics}
          initialMetrics={activeSession.my_participation.metrics}
        />
      )}

      <div className="bg-gray-800 rounded-xl p-4 w-full max-w-sm mb-6 border border-gray-700 flex flex-col gap-2.5">
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
        {/* PWA foreground tracking limitation notice (Requirement 21) */}
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 bg-gray-900/60 p-2 rounded-lg border border-gray-700/60">
          <span>📱</span>
          <span>Keep Gravity open for location-based activity tracking.</span>
        </div>
      </div>

      <button
        onClick={handleShowQR}
        className="w-full max-w-sm bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-3.5 px-6 rounded-xl transition-colors active:scale-[0.98] mb-3 min-h-[48px]"
      >
        Show Join QR
      </button>

      <button
        onClick={handleLeave}
        disabled={leaving}
        className="w-full max-w-sm bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-6 rounded-xl transition-colors shadow-lg shadow-red-600/20 active:scale-[0.98] disabled:opacity-50 min-h-[48px]"
      >
        {leaving ? 'Leaving...' : 'Finish / Leave'}
      </button>

      {/* QR Modal Overlay */}
      {showQR && (
        <div className="absolute inset-0 z-50 bg-gray-950/95 backdrop-blur-md flex flex-col items-center justify-center p-6 animate-fade-in">
          <h2 className="text-2xl font-bold text-white mb-1 text-center">Scan to join this activity</h2>
          <p className="text-gray-400 text-xs mb-6 text-center">{activeSession.activity_type_details.icon} {activeSession.label || activeSession.activity_type_details.name} • {activeSession.active_participants_count} active</p>
          
          <div className="bg-white p-5 rounded-2xl shadow-2xl mb-6 flex items-center justify-center">
            {loadingQR ? (
              <span className="text-gray-500 font-medium py-12">Loading QR...</span>
            ) : joinUrl ? (
              <QRCodeSVG value={joinUrl} size={220} />
            ) : null}
          </div>

          <div className="flex flex-col gap-2.5 w-full max-w-xs">
            <button
              onClick={handleCopyLink}
              disabled={!joinUrl}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-4 rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5 active:scale-95 min-h-[44px]"
            >
              <span>{copied ? '✓ Link Copied!' : '🔗 Copy Join Link'}</span>
            </button>
            <button
              onClick={() => setShowQR(false)}
              className="w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 hover:text-white font-bold py-3 px-6 rounded-xl text-xs transition-colors min-h-[44px] active:scale-95"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
