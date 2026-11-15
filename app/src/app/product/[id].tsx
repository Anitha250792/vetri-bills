import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { Image, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useRequireLogin } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, ErrorState, Loading, Page, QtyStepper, SectionTitle, Tag } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { expiryInfo, inr, shortDate } from '@/lib/format';
import { notify } from '@/lib/notify';
import { useAddToCart, useProduct, useToggleWishlist, useWishlistIds } from '@/lib/queries';
import { useLayout } from '@/lib/useLayout';
import { colors, radius, shadow } from '@/theme';

export default function ProductScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: p, isPending, isError, refetch } = useProduct(String(id));
  const wishlisted = useWishlistIds();
  const toggle = useToggleWishlist();
  const addToCart = useAddToCart();
  const requireLogin = useRequireLogin();
  const { wide } = useLayout();
  const [qty, setQty] = useState(1);

  if (isPending) {
    return (
      <Page>
        <AppHeader back title="Product" />
        <Loading />
      </Page>
    );
  }
  if (isError || !p) {
    return (
      <Page>
        <AppHeader back title="Product" />
        <ErrorState onRetry={() => refetch()} />
      </Page>
    );
  }

  const saved = wishlisted.has(p.id);
  const nearest = p.nearest_expiry ? expiryInfo(p.nearest_expiry) : null;
  const addNow = (then?: () => void) =>
    requireLogin(() =>
      addToCart.mutate(
        { productId: p.id, quantity: qty },
        {
          onSuccess: () => then?.(),
          onError: (e) => notify('Could not add to cart', errorMessage(e)),
        },
      ),
    );

  return (
    <Page>
      <AppHeader back title="Product" />
      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 40 }}>
        <View style={[styles.layout, wide && { flexDirection: 'row', gap: 24 }]}>
          <View style={[styles.imageBox, shadow, wide && { flex: 1, alignSelf: 'flex-start' }]}>
            {p.image ? (
              <Image source={{ uri: p.image }} style={styles.image} resizeMode="cover" />
            ) : (
              <Ionicons name="image-outline" size={64} color={colors.border} />
            )}
            {p.discount_percent > 0 ? (
              <View style={styles.discount}>
                <Text style={styles.discountText}>{p.discount_percent}% OFF</Text>
              </View>
            ) : null}
          </View>

          <View style={[styles.info, wide && { flex: 1 }]}>
            <Text style={styles.category}>{p.category_name}</Text>
            <Text style={styles.name}>{p.name}</Text>

            <View style={styles.priceRow}>
              <Text style={styles.price}>{inr(p.price)}</Text>
              {p.mrp && Number(p.mrp) > Number(p.price) ? <Text style={styles.mrp}>{inr(p.mrp)}</Text> : null}
            </View>
            <Text style={styles.taxNote}>
              {Number(p.tax_percent) > 0 ? `Inclusive of ${Number(p.tax_percent)}% tax` : 'No tax on this item'}
            </Text>

            <View style={styles.tagRow}>
              {!p.in_stock ? (
                <Tag label="Out of stock" fg={colors.danger} bg={colors.dangerSoft} icon="close-circle" />
              ) : p.is_low_stock ? (
                <Tag label={`Only ${p.stock_qty} left`} fg={colors.warn} bg={colors.warnSoft} icon="alert-circle" />
              ) : (
                <Tag label={`In stock (${p.stock_qty})`} fg={colors.greenDark} bg={colors.greenSoft} icon="checkmark-circle" />
              )}
              {nearest ? <Tag label={nearest.label} fg={nearest.fg} bg={nearest.bg} icon="time-outline" /> : null}
            </View>

            {p.in_stock ? (
              <View style={styles.qtyRow}>
                <Text style={styles.qtyLabel}>Quantity</Text>
                <QtyStepper value={qty} max={p.stock_qty} onChange={setQty} />
              </View>
            ) : null}

            <View style={styles.actions}>
              <Button
                title="Add to cart"
                icon="cart-outline"
                disabled={!p.in_stock}
                busy={addToCart.isPending}
                onPress={() => addNow(() => notify('Added to cart', `${qty} × ${p.name}`))}
                style={{ flex: 1 }}
              />
              <Button
                title="Buy now"
                icon="flash-outline"
                variant="secondary"
                disabled={!p.in_stock}
                onPress={() => addNow(() => router.push('/checkout'))}
                style={{ flex: 1 }}
              />
              <Button
                title=""
                icon={saved ? 'heart' : 'heart-outline'}
                variant="outline"
                onPress={() => requireLogin(() => toggle.mutate(p.id))}
                style={{ paddingHorizontal: 14 }}
              />
            </View>

            {p.description ? (
              <View style={{ marginTop: 22 }}>
                <SectionTitle>About this product</SectionTitle>
                <Text style={styles.description}>{p.description}</Text>
              </View>
            ) : null}

            <View style={{ marginTop: 22 }}>
              <SectionTitle>Expiry dates by batch</SectionTitle>
              {p.batches.length === 0 ? (
                <Text style={styles.description}>No batch information available.</Text>
              ) : (
                <View style={[styles.batches, shadow]}>
                  {p.batches.map((b, i) => {
                    const e = expiryInfo(b.expiry_date);
                    return (
                      <View key={b.id} style={[styles.batchRow, i > 0 && styles.batchDivider]}>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.batchNo}>Batch {b.batch_no}</Text>
                          <Text style={styles.batchSub}>
                            {b.qty} units · expires {shortDate(b.expiry_date)}
                          </Text>
                        </View>
                        <Tag label={e.label} fg={e.fg} bg={e.bg} />
                      </View>
                    );
                  })}
                </View>
              )}
              <Text style={styles.sku}>SKU {p.sku}</Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  layout: { gap: 18 },
  imageBox: {
    width: '100%',
    aspectRatio: 1,
    maxWidth: 520,
    alignSelf: 'center',
    backgroundColor: '#F0F3EE',
    borderRadius: radius.lg,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  image: { width: '100%', height: '100%' },
  discount: {
    position: 'absolute',
    top: 12,
    left: 12,
    backgroundColor: colors.navy,
    borderRadius: radius.pill,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  discountText: { color: colors.white, fontWeight: '800', fontSize: 12 },
  info: { gap: 6 },
  category: { color: colors.green, fontWeight: '800', fontSize: 13, textTransform: 'uppercase' },
  name: { fontSize: 26, fontWeight: '800', color: colors.text },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10, marginTop: 4 },
  price: { fontSize: 30, fontWeight: '800', color: colors.navy },
  mrp: { fontSize: 17, color: colors.muted, textDecorationLine: 'line-through' },
  taxNote: { color: colors.muted, fontSize: 13 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  qtyRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginTop: 14 },
  qtyLabel: { fontWeight: '700', color: colors.navy },
  actions: { flexDirection: 'row', gap: 10, marginTop: 16 },
  description: { color: colors.text, lineHeight: 22, fontSize: 15 },
  batches: { backgroundColor: colors.card, borderRadius: radius.md, overflow: 'hidden' },
  batchRow: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  batchDivider: { borderTopWidth: 1, borderTopColor: colors.border },
  batchNo: { fontWeight: '800', color: colors.text },
  batchSub: { color: colors.muted, fontSize: 13, marginTop: 2 },
  sku: { color: colors.muted, fontSize: 12, marginTop: 10 },
});
