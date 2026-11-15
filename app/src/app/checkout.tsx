import { Ionicons } from '@expo/vector-icons';
import { useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { router } from 'expo-router';
import React, { useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, EmptyState, Field, Loading, Page, SectionTitle } from '@/components/ui';
import { api, errorMessage } from '@/lib/api';
import { inr } from '@/lib/format';
import { notify } from '@/lib/notify';
import { useCart } from '@/lib/queries';
import { payWithRazorpay } from '@/lib/razorpayWeb';
import type { Bill, CheckoutResponse, Order } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

export default function Checkout() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const cart = useCart();
  const [address, setAddress] = useState(user?.address ?? '');
  const [busy, setBusy] = useState(false);

  if (!user) {
    return (
      <Page>
        <AppHeader back title="Checkout" />
        <EmptyState
          icon="lock-closed-outline"
          title="Sign in to check out"
          action={<Button title="Sign in" onPress={() => router.push('/login')} />}
        />
      </Page>
    );
  }
  if (cart.isPending) {
    return (
      <Page>
        <AppHeader back title="Checkout" />
        <Loading />
      </Page>
    );
  }
  const items = cart.data?.items ?? [];
  if (items.length === 0) {
    return (
      <Page>
        <AppHeader back title="Checkout" />
        <EmptyState
          icon="cart-outline"
          title="Your cart is empty"
          action={<Button title="Start shopping" onPress={() => router.navigate('/')} />}
        />
      </Page>
    );
  }

  const pay = async () => {
    setBusy(true);
    try {
      // 1. Turn the cart into an order and start the payment.
      const { data: started } = await api.post<CheckoutResponse>('/checkout/', { shipping_address: address.trim() });
      let proof;
      if (started.payment.mock) {
        // 2. Test mode: the server hands back what Razorpay would send after a successful payment.
        proof = (await api.post('/payments/mock-pay/', { razorpay_order_id: started.payment.razorpay_order_id })).data;
      } else if (Platform.OS === 'web') {
        // 2. Real Razorpay window in the browser.
        proof = await payWithRazorpay({
          keyId: started.payment.key_id,
          orderId: started.payment.razorpay_order_id,
          amountPaise: started.payment.amount,
          name: [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username,
          email: user.email,
          phone: user.phone,
        });
      } else {
        notify(
          'Card payment on the phone app',
          'Real Razorpay payments on Android need the native Razorpay module (see DEPLOY.md). Use the website, or keep MOCK_PAYMENTS=1 for testing.',
        );
        return;
      }
      // 3. The server checks the signature, takes the stock, makes the bill and empties the cart.
      const { data: done } = await api.post<{ order: Order; bill: Bill }>('/payments/verify/', proof);

      await Promise.all(
        ['cart', 'orders', 'bills', 'products', 'product', 'unread', 'notifications', 'report'].map((key) =>
          qc.invalidateQueries({ queryKey: [key] }),
        ),
      );
      router.replace({ pathname: '/order/[id]', params: { id: String(done.order.id), paid: '1' } });
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.data?.items?.length) {
        const lines = (e.response.data.items as { name: string; available: number }[])
          .map((i) => `${i.name}: only ${i.available} left`)
          .join('\n');
        notify('Some items are not available', lines);
        qc.invalidateQueries({ queryKey: ['cart'] });
      } else {
        notify('Payment not completed', errorMessage(e));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <AppHeader back title="Checkout" />
      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 40, gap: 18 }}>
        <View>
          <SectionTitle>Order summary</SectionTitle>
          <View style={[styles.card, shadow]}>
            {items.map((item, i) => (
              <View key={item.id} style={[styles.line, i > 0 && styles.divider]}>
                <Text style={styles.lineName} numberOfLines={2}>
                  {item.product.name}
                </Text>
                <Text style={styles.lineQty}>× {item.quantity}</Text>
                <Text style={styles.lineTotal}>{inr(item.line_total)}</Text>
              </View>
            ))}
            <View style={[styles.line, styles.divider]}>
              <Text style={[styles.lineName, { fontWeight: '800' }]}>Total (tax included)</Text>
              <Text style={styles.total}>{inr(cart.data?.total ?? 0)}</Text>
            </View>
          </View>
        </View>

        <View>
          <SectionTitle>Delivery address</SectionTitle>
          <Field
            label="Where should we deliver?"
            value={address}
            onChangeText={setAddress}
            multiline
            placeholder="House no, street, area, city, PIN"
          />
        </View>

        <View style={styles.testNote}>
          <Ionicons name="information-circle" size={20} color={colors.navy} />
          <Text style={styles.testNoteText}>Secure payment by Razorpay. In test mode no real money is charged. Your bill is created as soon as you pay.</Text>
        </View>

        <Button title={`Pay ${inr(cart.data?.total ?? 0)}`} icon="lock-closed" busy={busy} onPress={pay} />
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, overflow: 'hidden' },
  line: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  divider: { borderTopWidth: 1, borderTopColor: colors.border },
  lineName: { flex: 1, color: colors.text, fontWeight: '600' },
  lineQty: { color: colors.muted, fontWeight: '700' },
  lineTotal: { minWidth: 80, textAlign: 'right', fontWeight: '800', color: colors.navy },
  total: { fontSize: 20, fontWeight: '800', color: colors.green },
  testNote: { flexDirection: 'row', gap: 10, alignItems: 'center', backgroundColor: colors.navySoft, padding: 12, borderRadius: radius.md },
  testNoteText: { flex: 1, color: colors.navy, fontSize: 13 },
});
