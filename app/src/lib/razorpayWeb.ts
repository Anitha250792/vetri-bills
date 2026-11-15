/** Opens Razorpay Checkout in the browser (web build only). */
type Proof = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void; on: (e: string, cb: (r: unknown) => void) => void };
  }
}

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const s = document.createElement('script');
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Could not load Razorpay. Check your internet connection.'));
    document.body.appendChild(s);
  });
}

export async function payWithRazorpay(opts: {
  keyId: string;
  orderId: string;
  amountPaise: number;
  name: string;
  email: string;
  phone: string;
}): Promise<Proof> {
  await loadScript();
  return new Promise<Proof>((resolve, reject) => {
    const rzp = new window.Razorpay!({
      key: opts.keyId,
      order_id: opts.orderId,
      amount: opts.amountPaise,
      currency: 'INR',
      name: 'Vetri Bills',
      description: 'Vetri Technology Solutions',
      prefill: { name: opts.name, email: opts.email, contact: opts.phone },
      theme: { color: '#3DA535' },
      handler: (r: Proof) => resolve(r),
      modal: { ondismiss: () => reject(new Error('Payment was cancelled.')) },
    });
    rzp.on('payment.failed', () => reject(new Error('Payment failed. Please try again.')));
    rzp.open();
  });
}
