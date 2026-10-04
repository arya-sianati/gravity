import React, { createContext, useContext, useState, useEffect } from 'react';
import type {
  User,
  LoginPayload,
  RegisterPayload,
  UpdateProfilePayload,
} from '../api/client';
import {
  getMe,
  loginUser,
  registerUser,
  logoutUser,
  updateMe,
  initCsrf,
} from '../api/client';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<User>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async (): Promise<User | null> => {
    try {
      const currentUser = await getMe();
      setUser(currentUser);
      return currentUser;
    } catch {
      setUser(null);
      return null;
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        await initCsrf();
      } catch (err) {
        console.warn('Initial CSRF initialization error:', err);
      }
      try {
        await refreshUser();
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginPayload): Promise<User> => {
    const loggedUser = await loginUser(credentials);
    setUser(loggedUser);
    return loggedUser;
  };

  const register = async (payload: RegisterPayload): Promise<User> => {
    const registeredUser = await registerUser(payload);
    setUser(registeredUser);
    return registeredUser;
  };

  const logout = async (): Promise<void> => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
    }
  };

  const updateProfile = async (payload: UpdateProfilePayload): Promise<User> => {
    const updated = await updateMe(payload);
    setUser(updated);
    return updated;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
