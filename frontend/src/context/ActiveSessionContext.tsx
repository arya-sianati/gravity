import React, { createContext, useContext, useState, useEffect } from 'react';
import { getActiveParticipation, leaveSession } from '../api/sessions';
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

interface ActiveSessionContextType {
  activeSession: ActivitySession | null;
  setActiveSession: React.Dispatch<React.SetStateAction<ActivitySession | null>>;
  refreshActiveSession: () => Promise<void>;
  leaveActiveSession: () => Promise<any>;
  xpFeedback: XPFeedback | null;
  clearXPFeedback: () => void;
}

const ActiveSessionContext = createContext<ActiveSessionContextType | undefined>(undefined);

export const ActiveSessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, refreshUser } = useAuth();
  const [activeSession, setActiveSession] = useState<ActivitySession | null>(null);
  const [xpFeedback, setXpFeedback] = useState<XPFeedback | null>(null);
  
  const clearXPFeedback = () => setXpFeedback(null);
  
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

  useEffect(() => {
    refreshActiveSession();
  }, [user]);

  // Realtime updates handling
  useEffect(() => {
    if (lastMessage?.type === 'session.updated' || lastMessage?.type === 'session_updated') {
      const payload = lastMessage.payload;
      if (payload && activeSession && payload.session_id === activeSession.id) {
        if (payload.status !== 'active') {
          // Session ended or cancelled
          setActiveSession(null);
        } else {
          // Update active count
          setActiveSession(prev => prev ? {
            ...prev,
            active_participants_count: payload.participant_count
          } : null);
        }
      }
    }
  }, [lastMessage]);

  return (
    <ActiveSessionContext.Provider value={{ activeSession, setActiveSession, refreshActiveSession, leaveActiveSession, xpFeedback, clearXPFeedback }}>
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
