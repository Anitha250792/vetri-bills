import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'vetri-bills.tokens';

type Tokens = { access: string; refresh: string };

let current: Tokens | null = null;

export async function loadTokens(): Promise<Tokens | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    current = raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    current = null;
  }
  return current;
}

export async function saveTokens(tokens: Tokens) {
  current = tokens;
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(tokens));
  } catch {
    /* keep working in memory if storage is unavailable */
  }
}

export async function clearTokens() {
  current = null;
  try {
    await AsyncStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export const getAccess = () => current?.access ?? null;
export const getRefresh = () => current?.refresh ?? null;
