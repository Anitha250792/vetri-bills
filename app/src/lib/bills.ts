import { File, Paths } from 'expo-file-system';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { Platform } from 'react-native';

import { api } from './api';
import { API_BASE } from './config';
import { getAccess } from './tokens';
import type { Bill } from './types';

type BillRef = Pick<Bill, 'id' | 'bill_no'>;

/** Web: the PDF as a blob (the shared axios client adds the login token and refreshes it). */
async function fetchBlobUrl(bill: BillRef): Promise<string> {
  const { data } = await api.get<Blob>(`/bills/${bill.id}/download/`, { responseType: 'blob' });
  return URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
}

/** Phone: save the PDF in the app cache and return its local file address. */
async function downloadToCache(bill: BillRef): Promise<string> {
  await api.get('/auth/profile/'); // makes sure the login token is fresh before the download
  const target = new File(Paths.cache, `${bill.bill_no}.pdf`);
  const file = await File.downloadFileAsync(`${API_BASE}/bills/${bill.id}/download/`, target, {
    headers: { Authorization: `Bearer ${getAccess() ?? ''}` },
    idempotent: true,
  });
  return file.uri;
}

/** Web: saves the PDF. Phone: opens the share sheet (Save to Files, WhatsApp, email, ...). */
export async function downloadBill(bill: BillRef): Promise<void> {
  if (Platform.OS === 'web') {
    const url = await fetchBlobUrl(bill);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${bill.bill_no}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    return;
  }
  const uri = await downloadToCache(bill);
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(uri, { mimeType: 'application/pdf', dialogTitle: `Bill ${bill.bill_no}`, UTI: 'com.adobe.pdf' });
  }
}

/**
 * Phone: opens the system print dialog, where the user picks a Wi-Fi printer.
 * Web: opens the browser's print dialog for the PDF.
 */
export async function printBill(bill: BillRef): Promise<void> {
  if (Platform.OS === 'web') {
    const url = await fetchBlobUrl(bill);
    const frame = document.createElement('iframe');
    frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
    frame.src = url;
    frame.onload = () => {
      frame.contentWindow?.focus();
      frame.contentWindow?.print();
    };
    document.body.appendChild(frame);
    setTimeout(() => {
      frame.remove();
      URL.revokeObjectURL(url);
    }, 120000);
    return;
  }
  const uri = await downloadToCache(bill);
  await Print.printAsync({ uri });
}
