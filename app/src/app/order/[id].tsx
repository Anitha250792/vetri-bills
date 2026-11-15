import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { BillActions } from '@/components/BillActions';
import { Button, ErrorState, Loading, Page, SectionTitle, Tag } from '@/components/ui';
import { dateTime, inr } from '@/lib/format';
import { useOrder } from '@/lib/queries';
import { colors, radius, shadow } from '@/theme';

const statusTag = {
  paid: { label: 'Paid', fg: colors.greenDark, bg: colors.greenSoft },
  pending: { label: 'Awaiting payment', fg: colors.warn, bg: colors.warnSoft },
  failed: { label: 'Payment failed', fg: colors.danger, bg: colors.dangerSoft },
  cancelled: { label: 'Cancelled', fg: colors.muted, bg: '#EEE' },
} as const;

export default function OrderScreen() {
  const { id, paid } = useLocalSearchParams<{ id: string; paid?: string }>();
  const { data: order, isPending, isError, refetch } = useOrder(String(id));

  if (isPending) {
    return (
      <Page>
        <AppHeader back title="Order" />
        <Loading />
      </Page>
    );
  }
  if (isError || !order) {
    return (
      <Page>
        <AppHeader back title="Order" />
        <ErrorState onRetry={() => refetch()} />
      </Page>
    );
  }
  const tag = statusTag[order.status];

  return (
    <Page>
      <AppHeader back title={`Order #${order.id}`} />
      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 40, gap: 18 }}>
        {paid === '1' && order.status === 'paid' ? (
          <View style={styles.success}>
            <Ionicons name="checkmark-circle" size={54} color={colors.green} />
            <Text style={styles.successTitle}>Payment successful</Text>
            <Text style={styles.successText}>Thank you! Your bill is ready to download or print.</Text>
          </View>
        ) : null}

        <View style={[styles.card, shadow]}>
          <View style={styles.headRow}>
            <Text style={styles.date}>{dateTime(order.created_at)}</Text>
            <Tag label={tag.label} fg={tag.fg} bg={tag.bg} />
          </View>
          {order.shipping_address ? <Text style={styles.address}>Deliver to: {order.shipping_address}</Text> : null}
        </View>

        {order.bill ? (
          <View style={[styles.card, shadow, { gap: 12 }]}>
            <View style={styles.billRow}>
              <Ionicons name="document-text" size={26} color={colors.navy} />
              <View style={{ flex: 1 }}>
                <Text style={styles.billNo}>Bill {order.bill.bill_no}</Text>
                <Text style={styles.billSub}>PDF saved in your account</Text>
              </View>
            </View>
            <BillActions bill={order.bill} />
          </View>
        ) : null}

        <View>
          <SectionTitle>Items</SectionTitle>
          <View style={[styles.card, shadow, { padding: 0 }]}>
            {order.items.map((item, i) => (
              <View key={item.id} style={[styles.line, i > 0 && styles.divider]}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.itemName}>{item.product_name}</Text>
                  <Text style={styles.itemSub}>
                    {item.quantity} × {inr(item.unit_price)}
                  </Text>
                </View>
                <Text style={styles.itemTotal}>{inr(item.line_total)}</Text>
              </View>
            ))}
            <View style={[styles.totals, styles.divider]}>
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>Subtotal (excl. tax)</Text>
                <Text style={styles.totalValue}>{inr(order.subtotal)}</Text>
              </View>
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>Tax included</Text>
                <Text style={styles.totalValue}>{inr(order.tax_total)}</Text>
              </View>
              <View style={styles.totalRow}>
                <Text style={styles.grandLabel}>Total</Text>
                <Text style={styles.grand}>{inr(order.total)}</Text>
              </View>
            </View>
          </View>
        </View>

        <Button title="Continue shopping" variant="outline" onPress={() => router.navigate('/')} />
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  success: { alignItems: 'center', backgroundColor: colors.greenSoft, padding: 22, borderRadius: radius.lg, gap: 6 },
  successTitle: { fontSize: 20, fontWeight: '800', color: colors.greenDark },
  successText: { color: colors.text, textAlign: 'center' },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, gap: 8 },
  headRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  date: { fontWeight: '700', color: colors.text },
  address: { color: colors.muted, lineHeight: 20 },
  billRow: { flexDirection: 'row', gap: 12, alignItems: 'center' },
  billNo: { fontWeight: '800', color: colors.navy, fontSize: 16 },
  billSub: { color: colors.muted, fontSize: 13 },
  line: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  divider: { borderTopWidth: 1, borderTopColor: colors.border },
  itemName: { fontWeight: '700', color: colors.text },
  itemSub: { color: colors.muted, marginTop: 2, fontSize: 13 },
  itemTotal: { fontWeight: '800', color: colors.navy },
  totals: { padding: 14, gap: 6 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between' },
  totalLabel: { color: colors.muted },
  totalValue: { color: colors.text, fontWeight: '600' },
  grandLabel: { fontWeight: '800', color: colors.navy, fontSize: 16 },
  grand: { fontWeight: '800', color: colors.green, fontSize: 20 },
});
