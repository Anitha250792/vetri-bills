import { QueryClient, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './api';
import type { AdminBatch, AdminProduct } from './types';

export const useAdminProducts = (search: string) =>
  useQuery({
    queryKey: ['admin-products', search],
    queryFn: async () =>
      (await api.get<AdminProduct[]>('/admin/products/', { params: { search: search || undefined } })).data,
  });

export const useAdminProduct = (id: string | null) =>
  useQuery({
    queryKey: ['admin-product', id],
    enabled: !!id,
    queryFn: async () => (await api.get<AdminProduct>(`/admin/products/${id}/`)).data,
  });

export const useAdminBatches = (productId: string | null) =>
  useQuery({
    queryKey: ['admin-batches', productId],
    enabled: !!productId,
    queryFn: async () => (await api.get<AdminBatch[]>(`/admin/products/${productId}/batches/`)).data,
  });

/** After any change: refresh the shop pages, the alerts and the stock report too. */
export function refreshEverything(qc: QueryClient) {
  return Promise.all(
    ['admin-products', 'admin-product', 'admin-batches', 'products', 'product', 'notifications', 'unread', 'report', 'categories'].map(
      (key) => qc.invalidateQueries({ queryKey: [key] }),
    ),
  );
}

export const useRefreshEverything = () => {
  const qc = useQueryClient();
  return () => refreshEverything(qc);
};
