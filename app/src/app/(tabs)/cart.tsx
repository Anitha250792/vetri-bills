import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, EmptyState, ErrorState, Loading, Page, QtyStepper } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { inr } from '@/lib/format';
import { notify } from '@/lib/notify';
import { useCart, useRemoveFromCart, useSetCartQuantity } from '@/lib/queries';
import type { CartItem } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

function Row({ item }: { item: CartItem }) {
  const setQty = useSetCartQuantity();
  const remove = useRemoveFromCart();
  const p = item.product;
  return (
    <View style={[styles.row, shadow]}>
      <Pressable onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(p.id) } })}>
        {p.image ? <Image source={{ uri: p.image }} style={styles.thumb} /> : <View style={styles.thumb} />}
      </Pressable>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={styles.name} numberOfLines={2}>
          {p.name}
        </Text>
        <Text style={styles.unit}>{inr(p.price)} each</Text>
        <View style={styles.bottom}>
          <QtyStepper
            value={item.quantity}
            max={p.stock_qty}
            busy={setQty.isPending}
            onChange={(quantity) =>
              setQty.mutate(
                { productId: p.id, quantity },
                { onError: (e) => notify('Could not change quantity', errorMessage(e)) },
              )
            }
          />
          <Text style={styles.line}>{inr(item.line_total)}</Text>
        </View>
      </View>
      <Pressable accessibilityLabel={`Remove ${p.name}`} hitSlop={10} onPress={() => remove.mutate(p.id)}>
        <Ionicons name="trash-outline" size={20} color={colors.danger} />
      </Pressable>
    </View>
  );
}

export default function CartScreen() {
  const { user } = useAuth();
  const cart = useCart();

  return (
    <Page>
      <AppHeader title="My cart" />
      {!user ? (
        <EmptyState
          icon="cart-outline"
          title="Your cart is waiting"
          text="Sign in to add products and check out."
          action={<Button title="Sign in" onPress={() => router.push('/login')} />}
        />
      ) : cart.isPending ? (
        <Loading />
      ) : cart.isError ? (
        <ErrorState onRetry={() => cart.refetch()} />
      ) : cart.data.items.length === 0 ? (
        <EmptyState
          icon="cart-outline"
          title="Your cart is empty"
          text="Add some products and they will show up here."
          action={<Button title="Start shopping" onPress={() => router.navigate('/')} />}
        />
      ) : (
        <>
          <ScrollView contentContainerStyle={{ padding: 14, gap: 12, paddingBottom: 24 }}>
            {cart.data.items.map((item) => (
              <Row key={item.id} item={item} />
            ))}
          </ScrollView>
          <View style={[styles.summary, shadow]}>
            <View style={{ flex: 1 }}>
              <Text style={styles.sumNote}>
                Subtotal ({cart.data.item_count} {cart.data.item_count === 1 ? 'item' : 'items'}): {inr(cart.data.subtotal)}
              </Text>
              <Text style={styles.sumNote}>Tax: + {inr(cart.data.tax_total)}</Text>
              <Text style={styles.sumLabel}>Total</Text>
              <Text style={styles.sumValue}>{inr(cart.data.total)}</Text>
            </View>
            <Button title="Checkout" icon="arrow-forward" onPress={() => router.push('/checkout')} style={{ minWidth: 150 }} />
          </View>
        </>
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12, backgroundColor: colors.card, borderRadius: radius.lg, padding: 12, alignItems: 'flex-start' },
  thumb: { width: 84, height: 84, borderRadius: radius.md, backgroundColor: '#F0F3EE' },
  name: { fontSize: 15, fontWeight: '700', color: colors.text },
  unit: { color: colors.muted, fontSize: 13 },
  bottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 },
  line: { fontSize: 16, fontWeight: '800', color: colors.navy },
  summary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.card,
    padding: 16,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  sumLabel: { color: colors.muted, fontWeight: '600' },
  sumValue: { fontSize: 24, fontWeight: '800', color: colors.navy },
  sumNote: { color: colors.muted, fontSize: 12 },
});
