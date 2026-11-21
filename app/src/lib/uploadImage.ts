import * as ImagePicker from 'expo-image-picker';
import { Platform } from 'react-native';

import { api } from './api';
import type { AdminProduct } from './types';

export type PickedImage = { uri: string; name: string; type: string };

/** Opens the phone gallery (or the file chooser on the website). Returns null if cancelled. */
export async function pickImage(): Promise<PickedImage | null> {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsEditing: true,
    aspect: [1, 1],
    quality: 0.7,
  });
  if (result.canceled || !result.assets?.length) return null;
  const a = result.assets[0];
  return { uri: a.uri, name: a.fileName || 'photo.jpg', type: a.mimeType || 'image/jpeg' };
}

export async function uploadProductImage(productId: number | string, image: PickedImage): Promise<AdminProduct> {
  const form = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(image.uri)).blob();
    form.append('image', blob, image.name);
  } else {
    // React Native turns this object into a file part.
    form.append('image', { uri: image.uri, name: image.name, type: image.type } as unknown as Blob);
  }
  const { data } = await api.post<AdminProduct>(`/admin/products/${productId}/image/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    transformRequest: (d) => d,
  });
  return data;
}

export async function removeProductImage(productId: number | string): Promise<AdminProduct> {
  return (await api.delete<AdminProduct>(`/admin/products/${productId}/image/`)).data;
}
