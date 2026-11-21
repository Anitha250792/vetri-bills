import { router } from 'expo-router';
import React, { useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { AppHeader } from '@/components/AppHeader';
import { Button, EmptyState, ErrorState, Loading, Page, Tag } from '@/components/ui';
import { useAdminProducts } from '@/lib/adminQueries';
import { expiryInfo, inr } from '@/lib/format';
import { useDebounced } from '@/lib/useDebounced';
import { colors, radius, shadow } from '@/theme';

export default function Manage() {
  const [search, setSearch] = useState('');
  const q = useDebounced(search, 300);
  const list = useAdminProducts(q);

  return (
    <Page>
      <AppHeader title="Manage products" />
      <View style={styles.top}>
        <View style={styles.search}>
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="Search name or SKU"
            placeholderTextColor="#9AA0A6"
            style={styles.searchInput}
          />
        </View>
        <Button title="Add product" icon="add" small onPress={() => router.push({ pathname: '/admin/product/[id]', params: { id: 'new' } })} />
      </View>
      {list.isPending ? (
        <Loading />
      ) : list.isError ? (
        <ErrorState onRetry={() => list.refetch()} />
      ) : (
        <FlatList
          data={list.data}
          keyExtractor={(p) => String(p.id)}
          contentContainerStyle={{ padding: 14, gap: 10, paddingBottom: 30 }}
          refreshing={list.isRefetching}
          onRefresh={() => list.refetch()}
          ListEmptyComponent={<EmptyState icon="cube-outline" title="No products found" text="Tap Add product to create one." />}
          renderItem={({ item: p }) => {
            const exp = p.nearest_expiry ? expiryInfo(p.nearest_expiry) : null;
            return (
              <Pressable
                onPress={() => router.push({ pathname: '/admin/product/[id]', params: { id: String(p.id) } })}
                style={[styles.card, shadow, !p.is_active && { opacity: 0.6 }]}
              >
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={styles.name} numberOfLines={1}>
                    {p.name}
                  </Text>
                  <Text style={styles.sub}>
                    {p.category_name} · {p.sku} · {inr(p.price)}
                  </Text>
                  <View style={styles.tags}>
                    <Tag
                      label={p.stock_qty === 0 ? 'Out of stock' : `${p.stock_qty} in stock`}
                      fg={p.is_low_stock ? colors.danger : colors.greenDark}
                      bg={p.is_low_stock ? colors.dangerSoft : colors.greenSoft}
                    />
                    {exp ? <Tag label={exp.label} fg={exp.fg} bg={exp.bg} /> : null}
                    {!p.is_active ? <Tag label="Hidden" fg={colors.muted} bg="#EEE" /> : null}
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={20} color={colors.muted} />
              </Pressable>
            );
          }}
        />
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: 'row', gap: 10, alignItems: 'center', padding: 14, paddingBottom: 0 },
  search: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.white,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 12,
  },
  searchInput: { flex: 1, paddingVertical: 10, fontSize: 15, color: colors.text },
  card: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: colors.card, borderRadius: radius.lg, padding: 14 },
  name: { fontSize: 16, fontWeight: '800', color: colors.navy },
  sub: { color: colors.muted, fontSize: 13 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 2 },
});
