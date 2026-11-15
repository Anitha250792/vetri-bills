# Vetri Bills: Mobile + Web app (Expo)

One codebase runs on Android, iOS and the web, talking to the Django backend.

## Run
```powershell
cd app
npm install
copy .env.example .env      # then edit EXPO_PUBLIC_API_URL if needed
npx expo start --web        # browser
npx expo start              # phone: scan the QR with Expo Go
```
Start the backend first (`python manage.py runserver`; for a real phone use `0.0.0.0:8000` and your PC's Wi-Fi IP in `.env`).

## Screens
Home (search, categories, product grid) · Product detail · Wishlist · Cart · Checkout (test payment) · Order + bill (Download / Print) · My orders · My bills · Account · Admin only: Alerts, Stock & expiry report.

## Printing
Print opens the system print dialog: pick your Wi-Fi printer. On the web it opens the browser print dialog.

## Push notifications
Admin devices register for Expo push. Needs an EAS projectId and a development build (not Expo Go, not web). Added on Day 5.
