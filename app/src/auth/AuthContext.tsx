import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, setSessionLostHandler } from '@/lib/api';
import { registerForPush } from '@/lib/push';
import { clearTokens, loadTokens, saveTokens } from '@/lib/tokens';
import type { User } from '@/lib/types';

type RegisterInput = {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  phone?: string;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setSessionLostHandler(() => {
      setUser(null);
      queryClient.clear();
    });
    (async () => {
      const tokens = await loadTokens();
      if (tokens) {
        try {
          const { data } = await api.get<User>('/auth/profile/');
          setUser(data);
          if (data.role === 'admin') registerForPush();
        } catch {
          /* token no longer valid: stay logged out */
        }
      }
      setLoading(false);
    })();
  }, [queryClient]);

  const login = useCallback(
    async (identifier: string, password: string) => {
      const { data } = await api.post('/auth/login/', { username: identifier, password });
      await saveTokens({ access: data.access, refresh: data.refresh });
      queryClient.clear();
      setUser(data.user as User);
      if (data.user.role === 'admin') registerForPush();
    },
    [queryClient],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      await api.post('/auth/register/', input);
      await login(input.username, input.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    await clearTokens();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, loading, isAdmin: user?.role === 'admin', login, register, logout, setUser }),
    [user, loading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

/** Wrap an action that needs an account (add to cart, wishlist...): guests are sent to the login screen. */
export function useRequireLogin() {
  const { user } = useAuth();
  return useCallback(
    (action: () => void) => {
      if (user) action();
      else router.push('/login');
    },
    [user],
  );
}
