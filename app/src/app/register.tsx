import { router } from 'expo-router';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button, Field, Page } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { colors, radius, shadow } from '@/theme';

export default function Register() {
  const { register } = useAuth();
  const [form, setForm] = useState({ first_name: '', username: '', email: '', phone: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  const submit = async () => {
    if (!form.username.trim() || !form.email.trim() || form.password.length < 8) {
      setError('Username, email and a password of at least 8 characters are required.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        first_name: form.first_name.trim(),
        phone: form.phone.trim(),
      });
      router.replace('/');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <AppHeader back title="Create account" />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={[styles.card, shadow]}>
            <Field label="Your name" value={form.first_name} onChangeText={set('first_name')} placeholder="Full name" />
            <Field
              label="Username"
              value={form.username}
              onChangeText={set('username')}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="Choose a username"
            />
            <Field
              label="Email"
              value={form.email}
              onChangeText={set('email')}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="you@example.com"
            />
            <Field
              label="Phone (optional)"
              value={form.phone}
              onChangeText={set('phone')}
              keyboardType="phone-pad"
              placeholder="Mobile number"
            />
            <Field
              label="Password"
              value={form.password}
              onChangeText={set('password')}
              secureTextEntry
              placeholder="At least 8 characters"
              onSubmitEditing={submit}
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <Button title="Create account" icon="person-add-outline" busy={busy} onPress={submit} />
            <Button title="I already have an account" variant="outline" onPress={() => router.replace('/login')} style={{ marginTop: 10 }} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </Page>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 18, alignItems: 'center' },
  card: { width: '100%', maxWidth: 440, backgroundColor: colors.card, borderRadius: radius.lg, padding: 22 },
  error: { color: colors.danger, marginBottom: 12, fontWeight: '600' },
});
