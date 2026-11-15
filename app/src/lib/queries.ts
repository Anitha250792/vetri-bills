import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/auth/AuthContext';

import { api } from './api';
import type {
  AppNotification,
  Bill,
  Cart,
  Category,
  ExpiryReport,
  Order,
  Paginated,
  Product,
  ProductDetail,
  WishlistEntry,
} from './types';

// ---- catalogue (public) ------------------------------------------------------
export const useCategories = () =>
  useQuery({ queryKey: ['categories'], queryFn: async () => (await api.get<Category[]>('/categories/')).data });

export function useProducts(search: string, category: string | null) {
  return useInfiniteQuery({
    queryKey: ['products', search, category],
    initialPageParam: 1,
    queryFn: async ({ pageParam }) =>
      (
        await api.get<Paginated<Product>>('/products/', {
          params: { page: pageParam, search: search || undefined, category: category || undefined },
        })
      ).data,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
  });
}

export const useProduct = (id: string) =>
  useQuery({ queryKey: ['product', id], queryFn: async () => (await api.get<ProductDetail>(`/products/${id}/`)).data });

// ---- cart --------------------------------------------------------------------
export function useCart() {
  const { user } = useAuth();
  return useQuery({ queryKey: ['cart'], enabled: !!user, queryFn: async () => (await api.get<Cart>('/cart/')).data });
}

export function useAddToCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { productId: number; quantity?: number }) =>
      (await api.post<Cart>('/cart/items/', { product_id: v.productId, quantity: v.quantity ?? 1 })).data,
    onSuccess: (cart) => qc.setQueryData(['cart'], cart),
  });
}

export function useSetCartQuantity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { productId: number; quantity: number }) =>
      (await api.patch<Cart>(`/cart/items/${v.productId}/`, { quantity: v.quantity })).data,
    onSuccess: (cart) => qc.setQueryData(['cart'], cart),
  });
}

export function useRemoveFromCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (productId: number) => (await api.delete<Cart>(`/cart/items/${productId}/`)).data,
    onSuccess: (cart) => qc.setQueryData(['cart'], cart),
  });
}

// ---- wishlist ----------------------------------------------------------------
export function useWishlist() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['wishlist'],
    enabled: !!user,
    queryFn: async () => (await api.get<WishlistEntry[]>('/wishlist/')).data,
  });
}

export function useWishlistIds(): Set<number> {
  const { data } = useWishlist();
  return new Set((data ?? []).map((w) => w.product.id));
}

export function useToggleWishlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (productId: number) =>
      (await api.post<{ product_id: number; wishlisted: boolean }>('/wishlist/toggle/', { product_id: productId })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wishlist'] }),
  });
}

// ---- orders and bills --------------------------------------------------------
export function useOrders() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['orders'],
    enabled: !!user,
    queryFn: async () => (await api.get<Paginated<Order>>('/orders/')).data.results,
  });
}

export const useOrder = (id: string) =>
  useQuery({ queryKey: ['order', id], queryFn: async () => (await api.get<Order>(`/orders/${id}/`)).data });

export function useBills() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['bills'],
    enabled: !!user,
    queryFn: async () => (await api.get<Paginated<Bill>>('/bills/')).data.results,
  });
}

// ---- alerts (admin) ----------------------------------------------------------
export function useNotifications() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['notifications'],
    enabled: !!user,
    queryFn: async () => (await api.get<Paginated<AppNotification>>('/notifications/')).data.results,
  });
}

export function useUnreadCount() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['unread'],
    enabled: !!user,
    refetchInterval: 60000,
    queryFn: async () => (await api.get<{ unread: number }>('/notifications/unread-count/')).data.unread,
  });
}

export function useExpiryReport(days: number) {
  const { isAdmin } = useAuth();
  return useQuery({
    queryKey: ['report', days],
    enabled: isAdmin,
    queryFn: async () => (await api.get<ExpiryReport>('/admin/expiry-report/', { params: { days } })).data,
  });
}
