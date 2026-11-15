import { Platform } from 'react-native';

// Where the Django backend lives. Set EXPO_PUBLIC_API_URL in app/.env to change it.
//  - Web and iOS simulator: the same computer, so 127.0.0.1
//  - Android emulator: 10.0.2.2 is how the emulator reaches the computer
//  - A real phone: use the computer's Wi-Fi address, e.g. http://192.168.1.20:8000
const fromEnv = process.env.EXPO_PUBLIC_API_URL;
const fallback = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000';

export const API_URL = (fromEnv && fromEnv.length > 0 ? fromEnv : fallback).replace(/\/+$/, '');
export const API_BASE = `${API_URL}/api`;
