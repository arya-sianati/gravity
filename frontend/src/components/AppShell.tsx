import React, { useState, useEffect } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useActiveSession } from '../context/ActiveSessionContext';

export const AppShell: React.FC = () => {
  const { xpFeedback, autoStopFeedback, clearAutoStopFeedback } = useActiveSession();

  // Network online/offline status (Requirement 6 & 7)
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Native PWA Service Worker Update Prompt (Requirement 37 & 38)
  const [needRefresh, setNeedRefresh] = useState<boolean>(false);
  const [swUpdateFn, setSwUpdateFn] = useState<(() => void) | null>(null);

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistration().then((reg) => {
        if (!reg) return;
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              setNeedRefresh(true);
              setSwUpdateFn(() => () => {
                newWorker.postMessage({ type: 'SKIP_WAITING' });
                window.location.reload();
              });
            }
          });
        });
      });
    }
  }, []);

  return (
    <div className="flex flex-col h-[100dvh] w-full max-w-md mx-auto bg-black relative shadow-lg overflow-hidden select-none">
      {/* Offline Alert Banner (Requirement 6 & 7) */}
      {!isOnline && (
        <div className="bg-amber-950/95 border-b border-amber-600/70 text-amber-200 px-4 py-2 text-xs flex items-center justify-center gap-2 z-50 animate-fade-in backdrop-blur-md">
          <span>📡</span>
          <span className="font-semibold">You're offline</span>
          <span className="text-amber-300/80">• Live map and feeds will reconnect when online</span>
        </div>
      )}

      {/* PWA Update Ready Prompt (Requirement 37 & 38) */}
      {needRefresh && (
        <div className="absolute top-[calc(env(safe-area-inset-top,0px)+0.75rem)] left-1/2 -translate-x-1/2 z-50 flex items-center justify-between bg-indigo-950/95 border border-indigo-500/70 text-indigo-100 px-4 py-2.5 rounded-2xl shadow-2xl max-w-sm w-full mx-4 backdrop-blur-md text-xs">
          <div className="flex items-center gap-2">
            <span>⚡</span>
            <span>Gravity update ready</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => swUpdateFn ? swUpdateFn() : window.location.reload()}
              className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition-all active:scale-95"
            >
              Refresh
            </button>
            <button
              onClick={() => setNeedRefresh(false)}
              className="text-gray-400 hover:text-white p-1"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Auto-Stop Feedback Toast (Phase 18 Requirement 22) */}
      {autoStopFeedback && (
        <div className="absolute top-[calc(env(safe-area-inset-top,0px)+1rem)] left-1/2 -translate-x-1/2 z-50 flex items-center justify-between bg-amber-950/95 border border-amber-600/70 text-amber-200 px-4 py-3 rounded-2xl shadow-2xl max-w-sm w-full mx-4 backdrop-blur-md animate-fade-in">
          <div className="flex items-center space-x-2 text-xs font-medium">
            <span className="text-base">📍</span>
            <span>{autoStopFeedback}</span>
          </div>
          <button
            onClick={clearAutoStopFeedback}
            className="text-amber-400 hover:text-white text-xs font-bold ml-2 p-1"
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* XP Overlay Toast with Safe-Area & Stacking Management (Requirement 18) */}
      {xpFeedback && (
        <div className="absolute top-[calc(env(safe-area-inset-top,0px)+1rem)] left-1/2 -translate-x-1/2 z-50 flex flex-col items-center pointer-events-none gap-2 w-full px-4 max-w-sm max-h-56 overflow-y-auto">
          <div className="bg-indigo-600/90 backdrop-blur-md px-6 py-2.5 rounded-full text-white font-bold text-base shadow-[0_0_20px_rgba(79,70,229,0.5)] border border-indigo-400 whitespace-nowrap animate-bounce">
            +{xpFeedback.amount} XP
          </div>
          {xpFeedback.levelUp && (
            <div className="bg-yellow-500 text-black px-4 py-1 rounded-full font-black text-xs uppercase tracking-widest shadow-[0_0_15px_rgba(234,179,8,0.6)] whitespace-nowrap">
              Level Up! Lv {xpFeedback.newLevel}
            </div>
          )}
          {xpFeedback.badges_earned?.map((b) => (
            <div
              key={b.slug}
              className="bg-amber-600/95 text-white px-4 py-1.5 rounded-xl font-bold text-xs shadow-[0_0_15px_rgba(217,119,6,0.6)] border border-amber-400 flex items-center space-x-2 w-max"
            >
              <span className="text-base">{b.icon}</span>
              <span>{b.name} Earned!</span>
            </div>
          ))}
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        <Outlet />
      </main>

      {/* Bottom Navigation with Safe-Area & 44px Touch Targets (Requirement 9, 11, 12) */}
      <nav
        className="bg-gray-950/95 border-t border-gray-800/90 backdrop-blur-md flex justify-around items-center px-1 z-40 shrink-0"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 0.35rem)', paddingTop: '0.35rem' }}
      >
        <NavItem to="/" label="Map" icon="🗺️" />
        <NavItem to="/pulse" label="Pulse" icon="📡" />
        <NavItem to="/friends" label="Friends" icon="👥" />
        <NavItem to="/leaderboards" label="Rank" icon="🏆" />
        <NavItem to="/profile" label="Profile" icon="👤" />
      </nav>
    </div>
  );
};

const NavItem: React.FC<{ to: string; label: string; icon: string }> = ({ to, label, icon }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center min-w-[52px] min-h-[46px] px-2 py-1 rounded-xl transition-all active:scale-95 ${
          isActive
            ? 'text-indigo-400 bg-indigo-950/50 font-bold'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900/40'
        }`
      }
    >
      <span className="text-lg leading-none">{icon}</span>
      <span className="text-[10px] mt-1 tracking-tight leading-tight">{label}</span>
    </NavLink>
  );
};
