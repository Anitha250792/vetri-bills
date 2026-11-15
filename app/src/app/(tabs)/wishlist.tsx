import { router } from 'expo-router';
import React from 'react';
import { FlatList } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { ProductCard } from '@/components/ProductCard';
import { Button, EmptyState, ErrorState, Loading, Page } from '@/components/ui';
import { useWishlist } from '@/lib/queries';
import { useLayout } from '@/lib/useLayout';

export default function Wishlist() {
  const { user } = useAuth();
  const wishlist = useWishlist();
  const { columns, cardWidth, gap, gutter } = useLayout();

  return (
    <Page>
      <AppHeader title="My wishlist" />
      {!user ? (
        <EmptyState
          icon="heart-outline"
          title="Save the products you like"
          text="Sign in to build your wishlist."
          action={<Button title="Sign in" onPress={() => router.push('/login')} />}
        />
      ) : wishlist.isPending ? (
        <Loading />
      ) : wishlist.isError ? (
        <ErrorState onRetry={() => wishlist.refetch()} />
      ) : (
        <FlatList
          key={columns}
          data={wishlist.data}
          numColumns={columns}
          keyExtractor={(w) => String(w.id)}
          columnWrapperStyle={columns > 1 ? { gap } : undefined}
          contentContainerStyle={{ padding: gutter, paddingBottom: 24 }}
          renderItem={({ item }) => <ProductCard product={item.product} width={cardWidth} wishlisted />}
          ListEmptyComponent={
            <EmptyState icon="heart-outline" title="Your wishlist is empty" text="Tap the heart on any product to save it here." />
          }
        />
      )}
    </Page>
  );
}
