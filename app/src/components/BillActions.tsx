import React, { useState } from 'react';
import { View } from 'react-native';

import { errorMessage } from '@/lib/api';
import { downloadBill, printBill } from '@/lib/bills';
import { notify } from '@/lib/notify';

import { Button } from './ui';

/** Download and Print buttons for one bill. Printing opens the system dialog (pick a Wi-Fi printer). */
export function BillActions({ bill }: { bill: { id: number; bill_no: string } }) {
  const [busy, setBusy] = useState<'download' | 'print' | null>(null);

  const run = async (kind: 'download' | 'print') => {
    setBusy(kind);
    try {
      await (kind === 'download' ? downloadBill(bill) : printBill(bill));
    } catch (e) {
      notify(kind === 'download' ? 'Could not download the bill' : 'Could not print the bill', errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <View style={{ flexDirection: 'row', gap: 10 }}>
      <Button
        title="Download"
        icon="download-outline"
        small
        busy={busy === 'download'}
        disabled={busy === 'print'}
        onPress={() => run('download')}
        style={{ flex: 1 }}
      />
      <Button
        title="Print"
        icon="print-outline"
        small
        variant="secondary"
        busy={busy === 'print'}
        disabled={busy === 'download'}
        onPress={() => run('print')}
        style={{ flex: 1 }}
      />
    </View>
  );
}
