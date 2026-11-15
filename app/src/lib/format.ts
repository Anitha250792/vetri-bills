import { colors } from '@/theme';

export function inr(value: string | number): string {
  const n = typeof value === 'string' ? Number(value) : value;
  return '₹' + (Number.isFinite(n) ? n : 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

export function shortDate(iso: string): string {
  const d = new Date(iso.length <= 10 ? iso + 'T00:00:00' : iso);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}

export function daysUntil(isoDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(isoDate + 'T00:00:00');
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

/** "Expires in 3 days" with a colour: red = expired or very soon, amber = this week, green = fine. */
export function expiryInfo(isoDate: string): { label: string; fg: string; bg: string } {
  const d = daysUntil(isoDate);
  if (d < 0) return { label: 'Expired', fg: colors.danger, bg: colors.dangerSoft };
  if (d === 0) return { label: 'Expires today', fg: colors.danger, bg: colors.dangerSoft };
  if (d <= 7) return { label: d === 1 ? 'Expires tomorrow' : `Expires in ${d} days`, fg: colors.warn, bg: colors.warnSoft };
  return { label: `Exp ${shortDate(isoDate)}`, fg: colors.greenDark, bg: colors.greenSoft };
}
