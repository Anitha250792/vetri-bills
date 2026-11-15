import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { BillActions } from '@/components/BillActions';
import { Button, EmptyState, ErrorState, Loading, Page } from '@/components/ui';
import { dateTime, inr } from '@/lib/format';
import { useBills } from '@/lib/queries';
import { colors, radius, shadow } from '@/theme';

export default function Bills() {
  const { user } = useAuth();
  const bills = useBills();

  return (
    <Page>
      <AppHeader back title="My bills" />
      {!user ? (
        <EmptyState icon="lock-closed-outline" title="Sign in to see your bills" action={<Button title="Sign in" onPress={() => router.push('/login')} />} />
      ) : bills.isPending ? (
        <Loading />
      ) : bills.isError ? (
        <ErrorState onRetry={() => bills.refetch()} />
      ) : (
        <FlatList
          data={bills.data}
          keyExtractor={(b) => String(b.id)}
          contentContainerStyle={{ padding: 14, gap: 12 }}
          ListEmptyComponent={<EmptyState icon="document-text-outline" title="No bills yet" text="After you pay, your bill is saved here. You can download or print it any time." />}
          renderItem={({ item: b }) => (
            <View style={[styles.card, shadow]}>
              <View style={styles.row}>
                <Ionicons name="document-text" size={28} color={colors.navy} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.no}>{b.bill_no}</Text>
                  <Text style={styles.sub}>{dateTime(b.created_at)}</Text>
                </View>
                <Text style={styles.total}>{inr(b.total)}</Text>
              </View>
              <BillActions bill={b} />
            </View>
          )}
        />
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, gap: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  no: { fontWeight: '800', color: colors.navy, fontSize: 15 },
  sub: { color: colors.muted, marginTop: 2, fontSize: 13 },
  total: { fontSize: 18, fontWeight: '800', color: colors.text },
});
