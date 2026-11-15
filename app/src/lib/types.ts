export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  address: string;
  role: 'customer' | 'admin';
};

export type Category = { id: number; name: string; slug: string; image: string | null; product_count: number };

export type Product = {
  id: number;
  name: string;
  slug: string;
  category: number;
  category_name: string;
  image: string | null;
  price: string;
  mrp: string | null;
  discount_percent: number;
  stock_qty: number;
  in_stock: boolean;
  is_low_stock: boolean;
  nearest_expiry: string | null;
};

export type Batch = { id: number; batch_no: string; qty: number; expiry_date: string; days_to_expiry: number };

export type ProductDetail = Product & {
  sku: string;
  description: string;
  tax_percent: string;
  low_stock_threshold: number;
  batches: Batch[];
};

export type CartItem = { id: number; product: Product; quantity: number; line_total: string };
export type Cart = { items: CartItem[]; item_count: number; total: string };

export type WishlistEntry = { id: number; product: Product; added_at: string };

export type OrderItem = {
  id: number;
  product: number;
  product_name: string;
  unit_price: string;
  tax_percent: string;
  quantity: number;
  line_total: string;
};

export type Order = {
  id: number;
  status: 'pending' | 'paid' | 'failed' | 'cancelled';
  subtotal: string;
  tax_total: string;
  total: string;
  shipping_address: string;
  created_at: string;
  items: OrderItem[];
  bill: { id: number; bill_no: string } | null;
};

export type Bill = { id: number; bill_no: string; order_id: number; total: string; created_at: string; download_url: string };

export type CheckoutResponse = {
  order: Order;
  payment: {
    provider: string;
    key_id: string;
    razorpay_order_id: string;
    amount: number;
    currency: string;
    mock: boolean;
  };
};

export type NotificationType = 'expiry_soon' | 'expired' | 'low_stock';

export type AppNotification = {
  id: number;
  type: NotificationType;
  message: string;
  product: number | null;
  batch: number | null;
  is_read: boolean;
  created_at: string;
};

export type ReportBatch = {
  id: number;
  product_id: number;
  product_name: string;
  sku: string;
  batch_no: string;
  qty: number;
  expiry_date: string;
  days_to_expiry: number;
};

export type ReportLowStock = {
  id: number;
  name: string;
  sku: string;
  category_name: string;
  stock_qty: number;
  low_stock_threshold: number;
};

export type ExpiryReport = {
  as_of: string;
  warning_days: number;
  summary: { expired: number; expiring_soon: number; low_stock: number };
  expired: ReportBatch[];
  expiring_soon: ReportBatch[];
  low_stock: ReportLowStock[];
};
