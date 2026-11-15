import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { Chip, EmptyState, ErrorState, Loading, Page, SectionTitle, Tag } from '@/components/ui';
import { expiryInfo, shortDate } from '@/lib/format';
import { useExpiryReport } from '@/lib/queries';
import type { ReportBatch } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

function Stat({ value, label, fg, bg }: { value: number; label: string; fg: string; bg: string }) {
  return (
    <View style={[styles.stat, { backgroundColor: bg }]}>
      <Text style={[styles.statValue, { color: fg }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: fg }]}>{label}</Text>
    </View>
  );
}

function BatchRow({ b }: { b: ReportBatch }) {
  const info = expiryInfo(b.expiry_date);
  return (
    <Pressable
      onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(b.product_id) } })}
      style={[styles.row, shadow]}
    >
      <View style={{ flex: 1 }}>
        <Text style={styles.name}>{b.product_name}</Text>
        <Text style={styles.sub}>
          Batch {b.batch_no} · {b.qty} units · {shortDate(b.expiry_date)}
        </Text>
      </View>
      <Tag label={info.label} fg={info.fg} bg={info.bg} />
    </Pressable>
  );
}

export default function Report() {
  const [days, setDays] = useState(7);
  const report = useExpiryReport(days);

  return (
    <Page>
      <AppHeader title="Stock & expiry" />
      <ScrollView contentContainerStyle={{ padding: 14, gap: 18, paddingBottom: 40 }}>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          {[7, 14, 30].map((d) => (
            <Chip key={d} label={`Next ${d} days`} active={days === d} onPress={() => setDays(d)} />
          ))}
        </View>

        {report.isPending ? (
          <Loading />
        ) : report.isError ? (
          <ErrorState onRetry={() => report.refetch()} />
        ) : (
          <>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              <Stat value={report.data.summary.expired} label="Expired" fg={colors.danger} bg={colors.dangerSoft} />
              <Stat value={report.data.summary.expiring_soon} label="Expiring soon" fg={colors.warn} bg={colors.warnSoft} />
              <Stat value={report.data.summary.low_stock} label="Low stock" fg={colors.navy} bg={colors.navySoft} />
            </View>

            {report.data.expired.length === 0 && report.data.expiring_soon.length === 0 && report.data.low_stock.length === 0 ? (
              <EmptyState icon="checkmark-circle-outline" title="Everything looks good" text="No expired, expiring or low-stock items." />
            ) : null}

            {report.data.expired.length > 0 && (
              <View style={{ gap: 10 }}>
                <SectionTitle>Expired: remove from shelf</SectionTitle>
                {report.data.expired.map((b) => (
                  <BatchRow key={b.id} b={b} />
                ))}
              </View>
            )}
            {report.data.expiring_soon.length > 0 && (
              <View style={{ gap: 10 }}>
                <SectionTitle>Expiring within {days} days</SectionTitle>
                {report.data.expiring_soon.map((b) => (
                  <BatchRow key={b.id} b={b} />
                ))}
              </View>
            )}
            {report.data.low_stock.length > 0 && (
              <View style={{ gap: 10 }}>
                <SectionTitle>Low stock: reorder</SectionTitle>
                {report.data.low_stock.map((p) => (
                  <Pressable
                    key={p.id}
                    onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(p.id) } })}
                    style={[styles.row, shadow]}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={styles.name}>{p.name}</Text>
                      <Text style={styles.sub}>
                        {p.category_name} · reorder at {p.low_stock_threshold}
                      </Text>
                    </View>
                    <Tag label={p.stock_qty === 0 ? 'Out of stock' : `${p.stock_qty} left`} fg={colors.navy} bg={colors.navySoft} />
                  </Pressable>
                ))}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  stat: { flex: 1, borderRadius: radius.lg, padding: 14, alignItems: 'center' },
  statValue: { fontSize: 28, fontWeight: '800' },
  statLabel: { fontSize: 12, fontWeight: '700' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: colors.card, borderRadius: radius.lg, padding: 12 },
  name: { fontWeight: '700', color: colors.text },
  sub: { color: colors.muted, fontSize: 13, marginTop: 2 },
});
