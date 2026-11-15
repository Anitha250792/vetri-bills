import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, EmptyState, Field, Page, SectionTitle } from '@/components/ui';
import { api, errorMessage } from '@/lib/api';
import { API_URL } from '@/lib/config';
import { notify } from '@/lib/notify';
import type { User } from '@/lib/types';
import { colors, radius, shadow } from '@/theme';

function LinkRow({ icon, label, onPress }: { icon: keyof typeof Ionicons.glyphMap; label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.link}>
      <Ionicons name={icon} size={22} color={colors.navy} />
      <Text style={styles.linkText}>{label}</Text>
      <Ionicons name="chevron-forward" size={18} color={colors.muted} />
    </Pressable>
  );
}

export default function Account() {
  const { user, setUser, logout, isAdmin } = useAuth();
  const [first, setFirst] = useState('');
  const [last, setLast] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) {
      setFirst(user.first_name);
      setLast(user.last_name);
      setPhone(user.phone);
      setAddress(user.address);
    }
  }, [user]);

  if (!user) {
    return (
      <Page>
        <AppHeader title="Account" />
        <EmptyState
          icon="person-outline"
          title="Welcome to Vetri Bills"
          text="Sign in to see your orders, bills and wishlist."
          action={
            <View style={{ gap: 10 }}>
              <Button title="Sign in" onPress={() => router.push('/login')} />
              <Button title="Create account" variant="outline" onPress={() => router.push('/register')} />
            </View>
          }
        />
      </Page>
    );
  }

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch<User>('/auth/profile/', {
        first_name: first.trim(),
        last_name: last.trim(),
        phone: phone.trim(),
        address: address.trim(),
      });
      setUser(data);
      notify('Saved', 'Your details are updated.');
    } catch (e) {
      notify('Could not save', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <AppHeader title="Account" />
      <ScrollView contentContainerStyle={{ padding: 14, gap: 18, paddingBottom: 40 }}>
        <View style={[styles.hero, shadow]}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{(user.first_name || user.username).charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}</Text>
            <Text style={styles.email}>{user.email}</Text>
            {isAdmin ? <Text style={styles.role}>Shop admin</Text> : null}
          </View>
        </View>

        <View style={[styles.links, shadow]}>
          <LinkRow icon="receipt-outline" label="My orders" onPress={() => router.push('/orders')} />
          <LinkRow icon="document-text-outline" label="My bills" onPress={() => router.push('/bills')} />
        </View>

        <View style={{ gap: 12 }}>
          <SectionTitle>Your details</SectionTitle>
          <Field label="First name" value={first} onChangeText={setFirst} />
          <Field label="Last name" value={last} onChangeText={setLast} />
          <Field label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
          <Field label="Address" value={address} onChangeText={setAddress} multiline />
          <Button title="Save changes" busy={busy} onPress={save} />
        </View>

        <Button title="Sign out" variant="outline" icon="log-out-outline" onPress={logout} />
        <Text style={styles.api}>Server: {API_URL}</Text>
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  hero: { flexDirection: 'row', gap: 14, alignItems: 'center', backgroundColor: colors.card, borderRadius: radius.lg, padding: 16 },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: colors.green, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: colors.white, fontSize: 24, fontWeight: '800' },
  name: { fontSize: 18, fontWeight: '800', color: colors.navy },
  email: { color: colors.muted },
  role: { color: colors.greenDark, fontWeight: '700', marginTop: 2 },
  links: { backgroundColor: colors.card, borderRadius: radius.lg, overflow: 'hidden' },
  link: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16 },
  linkText: { flex: 1, fontWeight: '700', color: colors.text },
  api: { textAlign: 'center', color: colors.muted, fontSize: 12 },
});
