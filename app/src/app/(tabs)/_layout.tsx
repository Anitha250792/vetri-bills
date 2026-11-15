import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import React from 'react';
import { ColorValue, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuth } from '@/auth/AuthContext';
import { useCart, useUnreadCount } from '@/lib/queries';
import { colors } from '@/theme';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const icon =
  (active: IconName, inactive: IconName) =>
  ({ color, focused }: { color: ColorValue; focused: boolean }) => (
    <Ionicons name={focused ? active : inactive} size={24} color={color as string} />
  );

export default function TabsLayout() {
  const { isAdmin: admin, loading } = useAuth();
  const isAdmin = admin || loading; // keep admin tabs mounted while the saved login is restored
  const insets = useSafeAreaInsets();
  const cart = useCart();
  const unread = useUnreadCount();
  const cartCount = cart.data?.item_count ?? 0;
  const unreadCount = unread.data ?? 0;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.green,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '700' },
        tabBarStyle: {
          height: 66 + (Platform.OS === 'web' ? 0 : insets.bottom),
          paddingTop: 6,
          paddingBottom: Platform.OS === 'web' ? 8 : insets.bottom,
          borderTopColor: colors.border,
          backgroundColor: colors.white,
        },
        tabBarBadgeStyle: { backgroundColor: colors.danger, color: colors.white, fontWeight: '800' },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: icon('home', 'home-outline') }} />
      <Tabs.Screen name="wishlist" options={{ title: 'Wishlist', tabBarIcon: icon('heart', 'heart-outline') }} />
      <Tabs.Screen
        name="cart"
        options={{
          title: 'Cart',
          tabBarIcon: icon('cart', 'cart-outline'),
          tabBarBadge: cartCount > 0 ? cartCount : undefined,
        }}
      />
      <Tabs.Screen
        name="alerts"
        options={{
          title: 'Alerts',
          href: isAdmin ? undefined : null,
          tabBarIcon: icon('notifications', 'notifications-outline'),
          tabBarBadge: unreadCount > 0 ? unreadCount : undefined,
        }}
      />
      <Tabs.Screen
        name="report"
        options={{ title: 'Stock', href: isAdmin ? undefined : null, tabBarIcon: icon('stats-chart', 'stats-chart-outline') }}
      />
      <Tabs.Screen name="account" options={{ title: 'Account', tabBarIcon: icon('person', 'person-outline') }} />
    </Tabs>
  );
}
