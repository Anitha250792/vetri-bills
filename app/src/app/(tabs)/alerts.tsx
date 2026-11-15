import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import React from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { Button, EmptyState, ErrorState, Loading, Page } from '@/components/ui';
import { api } from '@/lib/api';
import { dateTime } from '@/lib/format';
import { useNotifications, useUnreadCount } from '@/lib/queries';
import type { AppNotification, NotificationType } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

const kinds: Record<NotificationType, { icon: keyof typeof Ionicons.glyphMap; fg: string; bg: string; label: string }> = {
  expired: { icon: 'alert-circle', fg: colors.danger, bg: colors.dangerSoft, label: 'Expired' },
  expiry_soon: { icon: 'time', fg: colors.warn, bg: colors.warnSoft, label: 'Expiring soon' },
  low_stock: { icon: 'cube', fg: colors.navy, bg: colors.navySoft, label: 'Low stock' },
};

export default function Alerts() {
  const qc = useQueryClient();
  const list = useNotifications();
  const unread = useUnreadCount();

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['notifications'] });
    qc.invalidateQueries({ queryKey: ['unread'] });
  };
  const markRead = useMutation({
    mutationFn: (id: number) => api.post(`/notifications/${id}/read/`),
    onSuccess: refresh,
  });
  const markAll = useMutation({ mutationFn: () => api.post('/notifications/read-all/'), onSuccess: refresh });

  const open = (n: AppNotification) => {
    if (!n.is_read) markRead.mutate(n.id);
    if (n.product) router.push({ pathname: '/product/[id]', params: { id: String(n.product) } });
  };

  return (
    <Page>
      <AppHeader title="Alerts" />
      {list.isPending ? (
        <Loading />
      ) : list.isError ? (
        <ErrorState onRetry={() => list.refetch()} />
      ) : (
        <FlatList
          data={list.data}
          keyExtractor={(n) => String(n.id)}
          contentContainerStyle={{ padding: 14, gap: 10 }}
          refreshing={list.isRefetching}
          onRefresh={() => list.refetch()}
          ListHeaderComponent={
            (unread.data ?? 0) > 0 ? (
              <View style={styles.bar}>
                <Text style={styles.barText}>{unread.data} unread</Text>
                <Button title="Mark all read" small variant="outline" busy={markAll.isPending} onPress={() => markAll.mutate()} />
              </View>
            ) : undefined
          }
          ListEmptyComponent={
            <EmptyState icon="notifications-outline" title="All clear" text="Expiry and low-stock alerts will appear here." />
          }
          renderItem={({ item: n }) => {
            const k = kinds[n.type];
            return (
              <Pressable onPress={() => open(n)} style={[styles.card, shadow, !n.is_read && styles.unread]}>
                <View style={[styles.icon, { backgroundColor: k.bg }]}>
                  <Ionicons name={k.icon} size={22} color={k.fg} />
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={[styles.kind, { color: k.fg }]}>{k.label}</Text>
                  <Text style={styles.msg}>{n.message}</Text>
                  <Text style={styles.time}>{dateTime(n.created_at)}</Text>
                </View>
                {!n.is_read ? <View style={styles.dot} /> : null}
              </Pressable>
            );
          }}
        />
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  barText: { fontWeight: '700', color: colors.navy },
  card: { flexDirection: 'row', gap: 12, backgroundColor: colors.card, borderRadius: radius.lg, padding: 12, alignItems: 'center' },
  unread: { borderLeftWidth: 4, borderLeftColor: colors.green },
  icon: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' },
  kind: { fontSize: 12, fontWeight: '800', textTransform: 'uppercase' },
  msg: { color: colors.text, lineHeight: 20 },
  time: { color: colors.muted, fontSize: 12 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.green },
});
