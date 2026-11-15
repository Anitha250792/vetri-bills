import { router } from 'expo-router';
import React, { useState } from 'react';
import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, Field, Page } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { colors, radius, shadow } from '@/theme';

const logo = require('../../assets/images/logo.png');

export default function Login() {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!identifier.trim() || !password) {
      setError('Enter your username (or email) and password.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await login(identifier.trim(), password);
      if (router.canGoBack()) router.back();
      else router.replace('/');
    } catch (e) {
      const status = (e as { response?: { status?: number } }).response?.status;
      setError(status === 401 ? 'Wrong username or password.' : errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <AppHeader back title="Sign in" />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={[styles.card, shadow]}>
            <Image source={logo} style={styles.logo} />
            <Text style={styles.title}>Welcome back</Text>
            <Text style={styles.sub}>Sign in to use your cart, wishlist and bills.</Text>

            <Field
              label="Username or email"
              value={identifier}
              onChangeText={setIdentifier}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="e.g. demo"
            />
            <Field
              label="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="Your password"
              onSubmitEditing={submit}
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}

            <Button title="Sign in" icon="log-in-outline" busy={busy} onPress={submit} />
            <Button
              title="Create an account"
              variant="outline"
              onPress={() => router.replace('/register')}
              style={{ marginTop: 10 }}
            />

            {__DEV__ ? (
              <View style={styles.demo}>
                <Text style={styles.demoTitle}>Test accounts (development only)</Text>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <Button
                    title="Customer"
                    small
                    variant="outline"
                    onPress={() => {
                      setIdentifier('demo');
                      setPassword('Demo@12345');
                    }}
                    style={{ flex: 1 }}
                  />
                  <Button
                    title="Shop admin"
                    small
                    variant="outline"
                    onPress={() => {
                      setIdentifier('admin');
                      setPassword('Admin@12345');
                    }}
                    style={{ flex: 1 }}
                  />
                </View>
              </View>
            ) : null}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </Page>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 18, alignItems: 'center' },
  card: { width: '100%', maxWidth: 440, backgroundColor: colors.card, borderRadius: radius.lg, padding: 22 },
  logo: { width: 72, height: 72, alignSelf: 'center', marginBottom: 10 },
  title: { fontSize: 22, fontWeight: '800', color: colors.navy, textAlign: 'center' },
  sub: { color: colors.muted, textAlign: 'center', marginTop: 4, marginBottom: 20 },
  error: { color: colors.danger, marginBottom: 12, fontWeight: '600' },
  demo: { marginTop: 22, paddingTop: 16, borderTopWidth: 1, borderTopColor: colors.border, gap: 8 },
  demoTitle: { fontSize: 12, color: colors.muted, textAlign: 'center' },
});
