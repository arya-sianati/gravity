import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getActiveParticipation, leaveSession, sendActivityHeartbeat } from '../api/sessions';
import type { ActivitySession } from '../api/sessions';
import { useAuth } from './AuthContext';
import { useGravitySocket } from '../lib/realtime/useGravitySocket';

interface BadgeEarned {
  slug: string;
  name: string;
  icon: string;
}

interface XPFeedback {
  amount: number;
  levelUp: boolean;
  newLevel: number;
  badges_earned: BadgeEarned[];
}

export interface GraceWarning {
  remainingSeconds: number;
}

interface ActiveSessionContextType {
  activeSession: ActivitySession | null;
  setActiveSession: React.Dispatch<React.SetStateAction<ActivitySession | null>>;
  refreshActiveSession: () => Promise<void>;
  leaveActiveSession: () => Promise<any>;
  xpFeedback: XPFeedback | null;
  clearXPFeedback: () => void;
  graceWarning: GraceWarning | null;
  autoStopFeedback: string | null;
  clearAutoStopFeedback: () => void;
}

const ActiveSessionContext = createContext<ActiveSessionContextType | undefined>(undefined);

export const ActiveSessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, refreshUser } = useAuth();
  const [activeSession, setActiveSession] = useState<ActivitySession | null>(null);
  const [xpFeedback, setXpFeedback] = useState<XPFeedback | null>(null);
  const [graceWarning, setGraceWarning] = useState<GraceWarning | null>(null);
  const [autoStopFeedback, setAutoStopFeedback] = useState<string | null>(null);
  
  const clearXPFeedback = () => setXpFeedback(null);
  const clearAutoStopFeedback = () => setAutoStopFeedback(null);
  
  const wsUrl = activeSession ? `/ws/gravity/session/${activeSession.id}/` : null;
  const { lastMessage } = useGravitySocket(wsUrl);

  const refreshActiveSession = async () => {
    if (!user) {
      setActiveSession(null);
      return;
    }
    try {
      const session = await getActiveParticipation();
      setActiveSession(session || null);
    } catch (err) {
      console.error('Failed to fetch active participation', err);
      setActiveSession(null);
    }
  };

  const leaveActiveSession = async () => {
    if (!activeSession) return null;
    try {
      const res = await leaveSession(activeSession.id);
      setActiveSession(null);
      setGraceWarning(null);
      if (res?.xp_awarded) {
        setXpFeedback({
          amount: res.xp_awarded,
          levelUp: !!res.level_up,
          newLevel: res.current_level,
          badges_earned: res.badges_earned || []
        });
        refreshUser();
        setTimeout(() => setXpFeedback(null), 5000);
      }
      return res;
    } catch (err) {
      console.error('Failed to leave session', err);
      throw err;
    }
  };

  const performHeartbeat = useCallback(async () => {
    if (!activeSession || !user) return;
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await sendActivityHeartbeat(pos.coords.latitude, pos.coords.longitude);
          if (res.auto_stopped) {
            setGraceWarning(null);
            setActiveSession(null);
            setAutoStopFeedback(res.completion?.detail || 'Activity ended because you left the activity area.');
            if (res.completion?.xp_awarded) {
              setXpFeedback({
                amount: res.completion.xp_awarded,
                levelUp: !!res.completion.level_up,
                newLevel: res.completion.current_level,
                badges_earned: res.completion.badges_earned || []
              });
              refreshUser();
            }
          } else if (!res.inside_activity_area && res.grace_remaining_seconds !== null && res.grace_remaining_seconds > 0) {
            setGraceWarning({ remainingSeconds: res.grace_remaining_seconds });
          } else if (res.inside_activity_area) {
            setGraceWarning(null);
          }
        } catch (err) {
          console.debug('Heartbeat submission skipped or failed', err);
        }
      },
      (err) => {
        console.debug('Geolocation unavailable for heartbeat', err);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 15000 }
    );
  }, [activeSession, user, refreshUser]);

  useEffect(() => {
    refreshActiveSession();
  }, [user]);

  // Periodic heartbeat every 25 seconds & visibilitychange handling
  useEffect(() => {
    if (!activeSession) {
      setGraceWarning(null);
      return;
    }

    const initialTimer = setTimeout(() => {
      performHeartbeat();
    }, 5000);

    const interval = setInterval(() => {
      performHeartbeat();
    }, 25000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        performHeartbeat();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [activeSession, performHeartbeat]);

  // Realtime updates handling
  useEffect(() => {
    if (lastMessage?.type === 'session.updated' || lastMessage?.type === 'session_updated') {
      const payload = lastMessage.payload;
      if (payload && activeSession && payload.session_id === activeSession.id) {
        if (payload.status !== 'active') {
          // Session ended or cancelled
          setActiveSession(null);
          setGraceWarning(null);
        } else {
          // Update active count
          setActiveSession(prev => prev ? {
            ...prev,
            active_participants_count: payload.participant_count
          } : null);
        }
      }
    }
  }, [lastMessage, activeSession]);

  return (
    <ActiveSessionContext.Provider value={{
      activeSession,
      setActiveSession,
      refreshActiveSession,
      leaveActiveSession,
      xpFeedback,
      clearXPFeedback,
      graceWarning,
      autoStopFeedback,
      clearAutoStopFeedback
    }}>
      {children}
    </ActiveSessionContext.Provider>
  );
};

export const useActiveSession = () => {
  const context = useContext(ActiveSessionContext);
  if (context === undefined) {
    throw new Error('useActiveSession must be used within an ActiveSessionProvider');
  }
  return context;
};
