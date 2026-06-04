'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, registerLogoutHandler } from '@/lib/api';
import type { User, LoginPayload, RegisterPayload } from '@/lib/types';
import { useRouter } from 'next/navigation';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  // Clear authentication state
  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
    setToken(null);
    setUser(null);
    router.push('/login');
  }, [router]);

  // Register the logout handler with registerLogoutHandler(logout) on mount.
  useEffect(() => {
    registerLogoutHandler(logout);
  }, [logout]);

  // On mount check token and attempt profile fetch
  useEffect(() => {
    const initializeAuth = async () => {
      if (typeof window !== 'undefined') {
        const storedToken = localStorage.getItem('token');
        if (storedToken) {
          setToken(storedToken);
          try {
            const userData = await authApi.getMe();
            setUser(userData);
          } catch (err) {
            console.error('Failed to restore session from token:', err);
            localStorage.removeItem('token');
            setToken(null);
          }
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  // Login handler
  const login = useCallback(async (payload: LoginPayload) => {
    setLoading(true);
    try {
      const response = await authApi.login(payload);
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', response.access_token);
      }
      setToken(response.access_token);
      setUser(response.user);
      router.push('/');
    } catch (err) {
      setLoading(false);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [router]);

  // Registration handler
  const register = useCallback(async (payload: RegisterPayload) => {
    setLoading(true);
    try {
      const response = await authApi.register(payload);
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', response.access_token);
      }
      setToken(response.access_token);
      setUser(response.user);
      router.push('/');
    } catch (err) {
      setLoading(false);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [router]);

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
