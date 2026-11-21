import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { DateField, isValidIso } from '@/components/DateField';
import { Button, Chip, EmptyState, ErrorState, Field, Loading, Page, SectionTitle, Tag } from '@/components/ui';
import { useAdminBatches, useAdminProduct, useRefreshEverything } from '@/lib/adminQueries';
import { api, errorMessage } from '@/lib/api';
import { expiryInfo, shortDate } from '@/lib/format';
import { confirm, notify } from '@/lib/notify';
import { useCategories } from '@/lib/queries';
import type { AdminBatch, AdminProduct } from '@/lib/types';
import { pickImage, removeProductImage, uploadProductImage, type PickedImage } from '@/lib/uploadImage';
import { colors, radius, shadow } from '@/theme';

const num = (s: string) => (s.trim() === '' ? NaN : Number(s));

export default function AdminProductScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const isNew = id === 'new';
  const { isAdmin } = useAuth();
  const refresh = useRefreshEverything();
  const categories = useCategories();
  const product = useAdminProduct(isNew ? null : String(id));
  const batches = useAdminBatches(isNew ? null : String(id));

  // product form
  const [name, setName] = useState('');
  const [category, setCategory] = useState<number | null>(null);
  const [price, setPrice] = useState('');
  const [mrp, setMrp] = useState('');
  const [tax, setTax] = useState('0');
  const [threshold, setThreshold] = useState('10');
  const [imageUrl, setImageUrl] = useState('');
  const [description, setDescription] = useState('');
  const [active, setActive] = useState(true);
  // first stock (new product) / stock form (existing product)
  const [batchNo, setBatchNo] = useState('');
  const [qty, setQty] = useState('');
  const [expiry, setExpiry] = useState('');
  const [editingBatch, setEditingBatch] = useState<AdminBatch | null>(null);
  const [picked, setPicked] = useState<PickedImage | null>(null); // chosen for a new product, uploaded on save
  const [savingImage, setSavingImage] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingBatch, setSavingBatch] = useState(false);

  const load = (p: AdminProduct) => {
    setName(p.name);
    setCategory(p.category);
    setPrice(p.price);
    setMrp(p.mrp ?? '');
    setTax(p.tax_percent);
    setThreshold(String(p.low_stock_threshold));
    setImageUrl(p.image_url);
    setDescription(p.description);
    setActive(p.is_active);
  };
  useEffect(() => {
    if (product.data) load(product.data);
  }, [product.data]);

  if (!isAdmin) {
    return (
      <Page>
        <AppHeader back title="Product" />
        <EmptyState icon="lock-closed-outline" title="Shop admins only" />
      </Page>
    );
  }
  if (!isNew && product.isPending) {
    return (
      <Page>
        <AppHeader back title="Product" />
        <Loading />
      </Page>
    );
  }
  if (!isNew && product.isError) {
    return (
      <Page>
        <AppHeader back title="Product" />
        <ErrorState onRetry={() => product.refetch()} />
      </Page>
    );
  }

  const clearBatchForm = () => {
    setBatchNo('');
    setQty('');
    setExpiry('');
    setEditingBatch(null);
  };

  const choosePicture = async () => {
    try {
      const image = await pickImage();
      if (!image) return;
      if (isNew) return setPicked(image);
      setSavingImage(true);
      await uploadProductImage(String(id), image);
      await refresh();
      notify('Picture saved', 'The new picture is now in the shop.');
    } catch (e) {
      notify('Could not use that picture', errorMessage(e));
    } finally {
      setSavingImage(false);
    }
  };

  const deletePicture = async () => {
    if (isNew) return setPicked(null);
    if (!(await confirm('Remove picture?', 'The product will show without a picture.', 'Remove'))) return;
    setSavingImage(true);
    try {
      await removeProductImage(String(id));
      setImageUrl('');
      await refresh();
    } catch (e) {
      notify('Could not remove', errorMessage(e));
    } finally {
      setSavingImage(false);
    }
  };

  const previewUri = picked?.uri ?? product.data?.image ?? (imageUrl.trim() || null);

  const saveProduct = async () => {
    if (!name.trim()) return notify('Name needed', 'Enter the product name.');
    if (!category) return notify('Category needed', 'Choose a category.');
    if (!(num(price) > 0)) return notify('Price needed', 'Enter the selling price.');
    if (mrp.trim() && num(mrp) < num(price)) return notify('Check MRP', 'MRP cannot be lower than the selling price.');
    if (!Number.isInteger(num(threshold)) || num(threshold) < 0) return notify('Low stock level', 'Enter a whole number, for example 10.');
    if (isNew && (qty.trim() || expiry.trim())) {
      if (!Number.isInteger(num(qty)) || num(qty) < 0) return notify('Stock quantity', 'Enter a whole number.');
      if (!isValidIso(expiry)) return notify('Expiry date', 'Pick the expiry date for this stock.');
    }
    const body: Record<string, unknown> = {
      name: name.trim(),
      category,
      price: num(price),
      mrp: mrp.trim() ? num(mrp) : null,
      tax_percent: num(tax) || 0,
      low_stock_threshold: num(threshold),
      image_url: imageUrl.trim(),
      description: description.trim(),
      is_active: active,
    };
    if (isNew && qty.trim() && isValidIso(expiry)) {
      body.initial_batch = { batch_no: batchNo.trim(), qty: num(qty), expiry_date: expiry };
    }
    setSaving(true);
    try {
      if (isNew) {
        const { data } = await api.post<AdminProduct>('/admin/products/', body);
        if (picked) {
          try {
            await uploadProductImage(data.id, picked);
          } catch (e) {
            notify('Product added, picture not saved', `${errorMessage(e)} Open the product and choose the picture again.`);
          }
        }
        await refresh();
        notify('Product added', `${data.name} is in the shop. Stock and expiry alerts are updated.`);
        router.replace({ pathname: '/admin/product/[id]', params: { id: String(data.id) } });
      } else {
        await api.patch(`/admin/products/${id}/`, body);
        await refresh();
        notify('Saved', 'Product details updated.');
      }
    } catch (e) {
      notify('Could not save', errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const saveBatch = async () => {
    if (!Number.isInteger(num(qty)) || num(qty) < 0) return notify('Quantity', 'Enter a whole number of units.');
    if (!isValidIso(expiry)) return notify('Expiry date', 'Pick the expiry date for this stock.');
    setSavingBatch(true);
    try {
      const body = { batch_no: batchNo.trim(), qty: num(qty), expiry_date: expiry };
      if (editingBatch) await api.patch(`/admin/batches/${editingBatch.id}/`, body);
      else await api.post(`/admin/products/${id}/batches/`, body);
      await refresh();
      clearBatchForm();
      notify('Stock saved', 'Stock and expiry alerts have been updated.');
    } catch (e) {
      notify('Could not save stock', errorMessage(e));
    } finally {
      setSavingBatch(false);
    }
  };

  const removeBatch = async (b: AdminBatch) => {
    if (!(await confirm('Remove this stock?', `Batch ${b.batch_no} (${b.qty} units) will be deleted.`, 'Remove'))) return;
    try {
      await api.delete(`/admin/batches/${b.id}/`);
      await refresh();
      if (editingBatch?.id === b.id) clearBatchForm();
    } catch (e) {
      notify('Could not remove', errorMessage(e));
    }
  };

  const editBatch = (b: AdminBatch) => {
    setEditingBatch(b);
    setBatchNo(b.batch_no);
    setQty(String(b.qty));
    setExpiry(b.expiry_date);
  };

  return (
    <Page>
      <AppHeader back title={isNew ? 'Add product' : 'Edit product'} />
      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        {!isNew && product.data ? (
          <View style={styles.summary}>
            <Tag
              label={product.data.stock_qty === 0 ? 'Out of stock' : `${product.data.stock_qty} in stock`}
              fg={product.data.is_low_stock ? colors.danger : colors.greenDark}
              bg={product.data.is_low_stock ? colors.dangerSoft : colors.greenSoft}
            />
            <Text style={styles.sku}>SKU {product.data.sku}</Text>
          </View>
        ) : null}

        <SectionTitle>Product details</SectionTitle>
        <Text style={styles.label}>Product picture</Text>
        <View style={styles.pictureRow}>
          {previewUri ? (
            <Image source={{ uri: previewUri }} style={styles.picture} />
          ) : (
            <View style={[styles.picture, styles.pictureEmpty]}>
              <Ionicons name="image-outline" size={34} color={colors.muted} />
            </View>
          )}
          <View style={{ flex: 1, gap: 8 }}>
            <Button
              title={previewUri ? 'Change picture' : 'Choose picture'}
              icon="images-outline"
              variant="secondary"
              small
              busy={savingImage}
              onPress={choosePicture}
            />
            {picked || product.data?.image ? (
              <Button title="Remove picture" icon="trash-outline" variant="danger" small onPress={deletePicture} />
            ) : null}
            <Text style={styles.help}>Pick a photo from your phone or computer.</Text>
          </View>
        </View>
        <View style={{ height: 14 }} />
        <Field label="Product name" value={name} onChangeText={setName} placeholder="e.g. Fresh Curd 400g" />
        <Text style={styles.label}>Category</Text>
        <View style={styles.chips}>
          {categories.data?.map((c) => (
            <Chip key={c.id} label={c.name} active={category === c.id} onPress={() => setCategory(c.id)} />
          ))}
        </View>
        <View style={{ height: 14 }} />
        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Field label="Selling price (₹)" value={price} onChangeText={setPrice} keyboardType="decimal-pad" placeholder="40" />
          </View>
          <View style={{ flex: 1 }}>
            <Field label="MRP (₹, optional)" value={mrp} onChangeText={setMrp} keyboardType="decimal-pad" placeholder="45" />
          </View>
        </View>
        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Field label="Tax % (added on top of price)" value={tax} onChangeText={setTax} keyboardType="decimal-pad" placeholder="5" />
          </View>
          <View style={{ flex: 1 }}>
            <Field label="Low stock alert at" value={threshold} onChangeText={setThreshold} keyboardType="number-pad" placeholder="10" />
          </View>
        </View>
        <Field label="Description" value={description} onChangeText={setDescription} multiline placeholder="Short description" />
        {!isNew ? (
          <View style={[styles.row, { alignItems: 'center', marginBottom: 14 }]}>
            <Text style={[styles.label, { flex: 1, marginBottom: 0 }]}>Visible in the shop</Text>
            <Chip label="Visible" active={active} onPress={() => setActive(true)} />
            <Chip label="Hidden" active={!active} onPress={() => setActive(false)} />
          </View>
        ) : null}

        {isNew ? (
          <View style={[styles.card, shadow]}>
            <SectionTitle>First stock</SectionTitle>
            <Text style={styles.help}>Add the first delivery so the alerts know the stock and expiry date. You can add more later.</Text>
            <View style={{ height: 10 }} />
            <Field label="Quantity received" value={qty} onChangeText={setQty} keyboardType="number-pad" placeholder="50" />
            <DateField label="Expiry date" value={expiry} onChange={setExpiry} />
            <Field label="Batch number (optional)" value={batchNo} onChangeText={setBatchNo} placeholder="Auto if empty" />
          </View>
        ) : null}

        <View style={{ height: 14 }} />
        <Button title={isNew ? 'Add product' : 'Save changes'} icon="checkmark" busy={saving} onPress={saveProduct} />

        {!isNew ? (
          <View style={{ marginTop: 26 }}>
            <SectionTitle>Stock and expiry</SectionTitle>
            {batches.isPending ? (
              <Loading />
            ) : batches.data && batches.data.length > 0 ? (
              <View style={{ gap: 10 }}>
                {batches.data.map((b) => {
                  const info = expiryInfo(b.expiry_date);
                  return (
                    <View key={b.id} style={[styles.batch, shadow, editingBatch?.id === b.id && { borderColor: colors.green, borderWidth: 2 }]}>
                      <View style={{ flex: 1, gap: 4 }}>
                        <Text style={styles.batchTitle}>
                          {b.qty} units · batch {b.batch_no}
                        </Text>
                        <Text style={styles.help}>Expires {shortDate(b.expiry_date)}</Text>
                        <View style={{ alignSelf: 'flex-start' }}>
                          <Tag label={info.label} fg={info.fg} bg={info.bg} />
                        </View>
                      </View>
                      <Pressable hitSlop={10} onPress={() => editBatch(b)} accessibilityLabel="Edit stock">
                        <Ionicons name="create-outline" size={22} color={colors.navy} />
                      </Pressable>
                      <Pressable hitSlop={10} onPress={() => removeBatch(b)} accessibilityLabel="Remove stock">
                        <Ionicons name="trash-outline" size={22} color={colors.danger} />
                      </Pressable>
                    </View>
                  );
                })}
              </View>
            ) : (
              <Text style={styles.help}>No stock added yet.</Text>
            )}

            <View style={[styles.card, shadow, { marginTop: 14 }]}>
              <SectionTitle>{editingBatch ? `Edit batch ${editingBatch.batch_no}` : 'Add new stock'}</SectionTitle>
              <View style={{ height: 8 }} />
              <Field label="Quantity" value={qty} onChangeText={setQty} keyboardType="number-pad" placeholder="50" />
              <DateField label="Expiry date" value={expiry} onChange={setExpiry} />
              <Field label="Batch number (optional)" value={batchNo} onChangeText={setBatchNo} placeholder="Auto if empty" />
              <Button title={editingBatch ? 'Save batch' : 'Add stock'} icon="add-circle" busy={savingBatch} onPress={saveBatch} />
              {editingBatch ? (
                <View style={{ marginTop: 10 }}>
                  <Button title="Cancel editing" variant="outline" onPress={clearBatchForm} />
                </View>
              ) : null}
            </View>
          </View>
        ) : null}
      </ScrollView>
    </Page>
  );
}

const styles = StyleSheet.create({
  pictureRow: { flexDirection: 'row', gap: 14, alignItems: 'center' },
  picture: { width: 104, height: 104, borderRadius: radius.md, backgroundColor: '#F0F3EE' },
  pictureEmpty: { alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.border, borderStyle: 'dashed' },
  label: { fontSize: 13, fontWeight: '700', color: colors.navy, marginBottom: 6 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  row: { flexDirection: 'row', gap: 12 },
  summary: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  sku: { color: colors.muted, fontWeight: '700' },
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14 },
  help: { color: colors.muted, fontSize: 13, lineHeight: 18 },
  batch: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: colors.card, borderRadius: radius.lg, padding: 14 },
  batchTitle: { fontWeight: '800', color: colors.navy, fontSize: 15 },
});
