import React from 'react';
import { Platform, StyleSheet, Text, TextInput, View } from 'react-native';

import { expiryInfo } from '@/lib/format';
import { colors } from '@/theme';

import { Chip, Tag } from './ui';

export const isoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export function isValidIso(s: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(s + 'T00:00:00');
  return !Number.isNaN(d.getTime()) && isoDate(d) === s;
}

function plus(days: number, months = 0): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  if (months) d.setMonth(d.getMonth() + months);
  d.setDate(d.getDate() + days);
  return isoDate(d);
}

const QUICK: { label: string; value: () => string }[] = [
  { label: '+7 days', value: () => plus(7) },
  { label: '+30 days', value: () => plus(30) },
  { label: '+3 months', value: () => plus(0, 3) },
  { label: '+6 months', value: () => plus(0, 6) },
  { label: '+1 year', value: () => plus(0, 12) },
];

/** Expiry date entry: type YYYY-MM-DD (a calendar on the web) or tap a quick button. */
export function DateField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const valid = isValidIso(value);
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={styles.label}>{label}</Text>
      {Platform.OS === 'web' ? (
        React.createElement('input', {
          type: 'date',
          value,
          onChange: (e: { target: { value: string } }) => onChange(e.target.value),
          style: { border: `1px solid ${colors.border}`, borderRadius: 12, padding: 12, fontSize: 16, background: '#fff', color: colors.text },
        })
      ) : (
        <TextInput
          value={value}
          onChangeText={onChange}
          placeholder="YYYY-MM-DD"
          placeholderTextColor="#9AA0A6"
          keyboardType="numbers-and-punctuation"
          maxLength={10}
          style={styles.input}
        />
      )}
      <View style={styles.quick}>
        {QUICK.map((q) => (
          <Chip key={q.label} label={q.label} onPress={() => onChange(q.value())} />
        ))}
      </View>
      {value ? (
        valid ? (
          <View style={{ alignSelf: 'flex-start', marginTop: 6 }}>
            {(() => {
              const info = expiryInfo(value);
              return <Tag label={info.label} fg={info.fg} bg={info.bg} />;
            })()}
          </View>
        ) : (
          <Text style={styles.error}>Use the format YYYY-MM-DD, for example 2027-03-31</Text>
        )
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 13, fontWeight: '700', color: colors.navy, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 12,
    fontSize: 16,
    backgroundColor: colors.white,
    color: colors.text,
  },
  quick: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  error: { color: colors.danger, fontSize: 12, marginTop: 6 },
});
