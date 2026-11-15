import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

import { API_BASE } from './config';
import { clearTokens, getAccess, getRefresh, saveTokens } from './tokens';

export const api = axios.create({ baseURL: API_BASE, timeout: 20000 });

// Called when the session can no longer be refreshed (the app then shows the login screen).
let onSessionLost: () => void = () => {};
export const setSessionLostHandler = (fn: () => void) => {
  onSessionLost = fn;
};

api.interceptors.request.use((config) => {
  const token = getAccess();
  if (token) config.headers.set('Authorization', `Bearer ${token}`);
  return config;
});

// One refresh at a time, shared by every request that failed with 401.
let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/token/refresh/`, { refresh }, { timeout: 20000 });
    await saveTokens({ access: data.access, refresh: data.refresh ?? refresh });
    return data.access as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const isAuthCall = original?.url?.includes('/auth/login/') || original?.url?.includes('/auth/token/refresh/');
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall && getRefresh()) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken().finally(() => (refreshing = null));
      const token = await refreshing;
      if (token) {
        original.headers.set('Authorization', `Bearer ${token}`);
        return api(original);
      }
      await clearTokens();
      onSessionLost();
    }
    return Promise.reject(error);
  },
);

/** A readable message for any failed request. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return `Cannot reach the server. Is the backend running?`;
    const data = error.response.data as Record<string, unknown> | undefined;
    if (data) {
      if (typeof data.detail === 'string') return data.detail;
      const first = Object.entries(data).find(([, v]) => v);
      if (first) {
        const [field, value] = first;
        const text = Array.isArray(value) ? String(value[0]) : String(value);
        return field === 'non_field_errors' ? text : `${field}: ${text}`;
      }
    }
    return `Request failed (${error.response.status}).`;
  }
  return fallback;
}
