import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { ProductCard } from '@/components/ProductCard';
import { Chip, EmptyState, ErrorState, Loading, Page } from '@/components/ui';
import { useCategories, useProducts, useWishlistIds } from '@/lib/queries';
import { useDebounced } from '@/lib/useDebounced';
import { useLayout } from '@/lib/useLayout';
import { colors, radius } from '@/theme';

export default function Home() {
  const [text, setText] = useState('');
  const search = useDebounced(text.trim(), 300);
  const [category, setCategory] = useState<string | null>(null);

  const categories = useCategories();
  const products = useProducts(search, category);
  const wishlisted = useWishlistIds();
  const { columns, cardWidth, gap, gutter } = useLayout();

  const items = products.data?.pages.flatMap((p) => p.results) ?? [];

  const header = (
    <View>
      <LinearGradient colors={[colors.navy, '#3C42A0']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.banner}>
        <View style={{ flex: 1 }}>
          <Text style={styles.bannerTitle}>Fresh stock, safe dates</Text>
          <Text style={styles.bannerText}>Every product shows its expiry date. Low stock is flagged before it runs out.</Text>
        </View>
        <Ionicons name="shield-checkmark" size={48} color={colors.green} />
      </LinearGradient>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
        <Chip label="All" active={category === null} onPress={() => setCategory(null)} />
        {(categories.data ?? []).map((c) => (
          <Chip
            key={c.id}
            label={`${c.name} (${c.product_count})`}
            active={category === c.slug}
            onPress={() => setCategory(category === c.slug ? null : c.slug)}
          />
        ))}
      </ScrollView>
    </View>
  );

  return (
    <Page>
      <AppHeader>
        <View style={styles.search}>
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder="Search products"
            placeholderTextColor="#9AA0A6"
            returnKeyType="search"
            style={styles.searchInput}
          />
          {text.length > 0 ? (
            <Pressable accessibilityLabel="Clear search" hitSlop={8} onPress={() => setText('')}>
              <Ionicons name="close-circle" size={18} color={colors.muted} />
            </Pressable>
          ) : null}
        </View>
      </AppHeader>

      {products.isPending ? (
        <Loading />
      ) : products.isError ? (
        <ErrorState onRetry={() => products.refetch()} />
      ) : (
        <FlatList
          key={columns}
          data={items}
          numColumns={columns}
          keyExtractor={(p) => String(p.id)}
          ListHeaderComponent={header}
          columnWrapperStyle={columns > 1 ? { gap } : undefined}
          contentContainerStyle={{ paddingHorizontal: gutter, paddingBottom: 24 }}
          renderItem={({ item }) => <ProductCard product={item} width={cardWidth} wishlisted={wishlisted.has(item.id)} />}
          ListEmptyComponent={
            <EmptyState icon="search-outline" title="No products found" text="Try a different word or category." />
          }
          ListFooterComponent={products.isFetchingNextPage ? <Loading /> : undefined}
          onEndReachedThreshold={0.4}
          onEndReached={() => {
            if (products.hasNextPage && !products.isFetchingNextPage) products.fetchNextPage();
          }}
          refreshControl={
            <RefreshControl
              refreshing={products.isRefetching && !products.isFetchingNextPage}
              onRefresh={() => void products.refetch()}
              tintColor={colors.green}
            />
          }
        />
      )}
    </Page>
  );
}

const styles = StyleSheet.create({
  search: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.white,
    borderRadius: radius.pill,
    paddingHorizontal: 14,
    minHeight: 42,
  },
  searchInput: { flex: 1, fontSize: 15, color: colors.text, paddingVertical: 8, outlineStyle: 'none' } as never,
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 18,
    borderRadius: radius.lg,
    marginTop: 14,
  },
  bannerTitle: { color: colors.white, fontSize: 19, fontWeight: '800' },
  bannerText: { color: '#D9DBF3', fontSize: 13, marginTop: 4, lineHeight: 18 },
  chips: { gap: 8, paddingVertical: 14 },
});
