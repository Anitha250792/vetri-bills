import { router } from 'expo-router';
import React from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { BillActions } from '@/components/BillActions';
import { Button, EmptyState, ErrorState, Loading, Page, Tag } from '@/components/ui';
import { dateTime, inr } from '@/lib/format';
import { useOrders } from '@/lib/queries';
import { colors, radius, shadow } from '@/theme';

const statusTag = {
  paid: { label: 'Paid', fg: colors.greenDark, bg: colors.greenSoft },
  pending: { label: 'Awaiting payment', fg: colors.warn, bg: colors.warnSoft },
  failed: { label: 'Payment failed', fg: colors.danger, bg: colors.dangerSoft },
  cancelled: { label: 'Cancelled', fg: colors.muted, bg: '#EEE' },
} as const;

export default function Orders() {
  const { user } = useAuth();
  const orders = useOrders();

  return (
    <Page>
      <AppHeader back title="My orders" />
      {!user ? (
        <EmptyState icon="lock-closed-outline" title="Sign in to see your orders" action={<Button title="Sign in" onPress={() => router.push('/login')} />} />
      ) : orders.isPending ? (
        <Loading />
      ) : orders.isError ? (
        <ErrorState onRetry={() => orders.refetch()} />
      ) : (
        <FlatList
          data={orders.data}
          keyExtractor={(o) => String(o.id)}
          contentContainerStyle={{ padding: 14, gap: 12 }}
          ListEmptyComponent={<EmptyState icon="receipt-outline" title="No orders yet" text="Your orders and bills will appear here." />}
          renderItem={({ item: o }) => {
            const tag = statusTag[o.status];
            return (
              <Pressable
                onPress={() => router.push({ pathname: '/order/[id]', params: { id: String(o.id) } })}
                style={[styles.card, shadow]}
              >
                <View style={styles.head}>
                  <Text style={styles.title}>Order #{o.id}</Text>
                  <Tag label={tag.label} fg={tag.fg} bg={tag.bg} />
                </View>
                <Text style={styles.sub}>
                  {dateTime(o.created_at)} · {o.items.length} {o.items.length === 1 ? 'item' : 'items'}
                </Text>
                <Text style={styles.total}>{inr(o.total)}</Text>
                {o.bill ? <BillActions bill={o.bill} /> : null}
              </Pressable>
            );
          }}
        />
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, gap: 8 },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 16, fontWeight: '800', color: colors.navy },
  sub: { color: colors.muted },
  total: { fontSize: 20, fontWeight: '800', color: colors.text },
});
