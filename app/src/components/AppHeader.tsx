import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, MAX_WIDTH } from '@/theme';

const logo = require('../../assets/images/logo.png');

/** Green brand bar. With `back` it shows a back arrow and a title instead of the logo. */
export function AppHeader({
  title,
  back,
  children,
}: {
  title?: string;
  back?: boolean;
  children?: React.ReactNode;
}) {
  const insets = useSafeAreaInsets();
  return (
    <LinearGradient
      colors={[colors.greenDark, colors.green]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{ paddingTop: insets.top + 10, paddingBottom: 12, alignItems: 'center' }}
    >
      <View style={styles.inner}>
        <View style={styles.row}>
          {back ? (
            <Pressable
              accessibilityLabel="Go back"
              hitSlop={10}
              onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
              style={styles.backBtn}
            >
              <Ionicons name="arrow-back" size={22} color={colors.white} />
            </Pressable>
          ) : (
            <Image source={logo} style={styles.logo} />
          )}
          <Text style={styles.title} numberOfLines={1}>
            {title ?? 'Vetri Bills'}
          </Text>
        </View>
        {children}
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  inner: { width: '100%', maxWidth: MAX_WIDTH, paddingHorizontal: 14, gap: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  logo: { width: 38, height: 38, borderRadius: 19, backgroundColor: colors.white },
  backBtn: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, color: colors.white, fontSize: 20, fontWeight: '800' },
});
