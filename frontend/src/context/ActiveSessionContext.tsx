import React, { createContext, useContext, useState, useEffect } from 'react';
import { getActiveParticipation, leaveSession } from '../api/sessions';
import type { ActivitySession } from '../api/sessions';
import { useAuth } from './AuthContext';
import { useGravitySocket } from '../lib/realtime/useGravitySocket';

interface ActiveSessionContextType {
  activeSession: ActivitySession | null;
  setActiveSession: React.Dispatch<React.SetStateAction<ActivitySession | null>>;
  refreshActiveSession: () => Promise<void>;
  leaveActiveSession: () => Promise<void>;
}

const ActiveSessionContext = createContext<ActiveSessionContextType | undefined>(undefined);

export const ActiveSessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [activeSession, setActiveSession] = useState<ActivitySession | null>(null);
  
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
    if (!activeSession) return;
    try {
      await leaveSession(activeSession.id);
      setActiveSession(null);
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
    <ActiveSessionContext.Provider value={{ activeSession, setActiveSession, refreshActiveSession, leaveActiveSession }}>
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
