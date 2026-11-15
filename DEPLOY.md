# Vetri Bills: Go live (Day 5)

Order: 1) backend online  2) website online  3) Android APK  4) real Razorpay test payments.

## 1. Backend on Render (free)
1. Put the project on GitHub (repo root has `render.yaml`, `backend/`, `app/`).
2. render.com > New > Blueprint > select the repo > Apply. It builds the API and a PostgreSQL database.
3. When it is live, open `https://<your-service>.onrender.com/api/docs/`. Demo data and product pictures are created on the first deploy (`SEED_DEMO=1`).
4. Then in Render > Environment: set `SEED_DEMO=0`, change the demo passwords in admin (`/admin`), and update `CORS_ALLOWED_ORIGINS` to your website address.
Note: the free plan sleeps after 15 min idle (first request takes ~50 s), and the free database expires after 30 days. Use a paid plan for real shop use.

## 2. Website (Netlify)
```powershell
cd app
$env:EXPO_PUBLIC_API_URL="https://<your-service>.onrender.com"
npx expo export --platform web
```
Drag the `dist` folder onto app.netlify.com/drop. (`public/_redirects` already makes page refresh work.)

## 3. Android APK (EAS)
```powershell
cd app
npm install -g eas-cli
eas login
eas init            # creates the project id (needed for push notifications)
eas build -p android --profile preview
```
Edit `EXPO_PUBLIC_API_URL` in `eas.json` first. EAS gives you a download link for the .apk; install it on the phone. Admin phones then receive expiry and low-stock push alerts.

## 4. Real Razorpay (test mode)
1. razorpay.com > Settings > API Keys > generate **Test** keys.
2. On Render set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and `MOCK_PAYMENTS=0`.
3. The website now opens the real Razorpay window (test card 4111 1111 1111 1111, any future date, any CVV).
4. The Android app still needs the native Razorpay module (`react-native-razorpay`, development build). Until then keep payments on the website or MOCK_PAYMENTS=1.

## Printing
Bills print through the phone/browser print dialog (any Wi-Fi printer, or "Save as PDF"). Thermal receipt printers (ESC/POS) are an optional extra.
