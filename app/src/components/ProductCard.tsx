import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { useRequireLogin } from '@/auth/AuthContext';
import { errorMessage } from '@/lib/api';
import { expiryInfo, inr } from '@/lib/format';
import { notify } from '@/lib/notify';
import { useAddToCart, useToggleWishlist } from '@/lib/queries';
import type { Product } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

import { Tag } from './ui';

export function ProductCard({
  product,
  width,
  wishlisted,
}: {
  product: Product;
  width: number;
  wishlisted: boolean;
}) {
  const requireLogin = useRequireLogin();
  const addToCart = useAddToCart();
  const toggle = useToggleWishlist();
  const expiry = product.nearest_expiry ? expiryInfo(product.nearest_expiry) : null;

  const add = () =>
    requireLogin(() =>
      addToCart.mutate(
        { productId: product.id },
        { onError: (e) => notify('Could not add to cart', errorMessage(e)) },
      ),
    );

  return (
    <Pressable
      onPress={() => router.push({ pathname: '/product/[id]', params: { id: String(product.id) } })}
      style={[styles.card, shadow, { width }]}
    >
      <View style={[styles.imageBox, { height: width }]}>
        {product.image ? (
          <Image source={{ uri: product.image }} style={styles.image} resizeMode="cover" />
        ) : (
          <Ionicons name="image-outline" size={40} color={colors.border} />
        )}
        {product.discount_percent > 0 ? (
          <View style={styles.discount}>
            <Text style={styles.discountText}>{product.discount_percent}% OFF</Text>
          </View>
        ) : null}
        <Pressable
          accessibilityLabel={wishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
          hitSlop={8}
          onPress={() => requireLogin(() => toggle.mutate(product.id))}
          style={styles.heart}
        >
          <Ionicons
            name={wishlisted ? 'heart' : 'heart-outline'}
            size={20}
            color={wishlisted ? colors.danger : colors.muted}
          />
        </Pressable>
      </View>

      <View style={styles.body}>
        <Text style={styles.category} numberOfLines={1}>
          {product.category_name}
        </Text>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>

        <View style={styles.priceRow}>
          <Text style={styles.price}>{inr(product.price)}</Text>
          {product.mrp && Number(product.mrp) > Number(product.price) ? (
            <Text style={styles.mrp}>{inr(product.mrp)}</Text>
          ) : null}
        </View>

        <View style={styles.tags}>
          {!product.in_stock ? (
            <Tag label="Out of stock" fg={colors.danger} bg={colors.dangerSoft} />
          ) : product.is_low_stock ? (
            <Tag label={`Only ${product.stock_qty} left`} fg={colors.warn} bg={colors.warnSoft} />
          ) : null}
          {expiry ? <Tag label={expiry.label} fg={expiry.fg} bg={expiry.bg} icon="time-outline" /> : null}
        </View>

        <Pressable
          accessibilityRole="button"
          disabled={!product.in_stock || addToCart.isPending}
          onPress={add}
          style={({ pressed }) => [
            styles.addBtn,
            (!product.in_stock || pressed) && { opacity: product.in_stock ? 0.85 : 0.4 },
          ]}
        >
          {addToCart.isPending ? (
            <ActivityIndicator size="small" color={colors.white} />
          ) : (
            <>
              <Ionicons name="cart-outline" size={16} color={colors.white} />
              <Text style={styles.addText}>Add to cart</Text>
            </>
          )}
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, overflow: 'hidden', marginBottom: 12 },
  imageBox: { backgroundColor: '#F0F3EE', alignItems: 'center', justifyContent: 'center' },
  image: { width: '100%', height: '100%' },
  discount: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: colors.navy,
    borderRadius: radius.pill,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  discountText: { color: colors.white, fontSize: 10, fontWeight: '800' },
  heart: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(255,255,255,0.95)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { padding: 10, gap: 3 },
  category: { fontSize: 11, color: colors.muted, fontWeight: '600' },
  name: { fontSize: 14, fontWeight: '700', color: colors.text, minHeight: 36 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 6, marginTop: 2 },
  price: { fontSize: 17, fontWeight: '800', color: colors.navy },
  mrp: { fontSize: 12, color: colors.muted, textDecorationLine: 'line-through' },
  tags: { gap: 4, marginTop: 4, minHeight: 22 },
  addBtn: {
    marginTop: 8,
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.green,
    borderRadius: radius.md,
    minHeight: 38,
  },
  addText: { color: colors.white, fontWeight: '800', fontSize: 13 },
});
