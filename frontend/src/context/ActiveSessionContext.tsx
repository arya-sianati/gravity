import React, { createContext, useContext, useState, useEffect } from 'react';
import { getActiveParticipation, leaveSession } from '../api/sessions';
import type { ActivitySession } from '../api/sessions';
import { useAuth } from './AuthContext';

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
