# Backend on Vercel + Neon

1. Load the Neon database from your PC (PowerShell, backend folder, venv active):
```powershell
$env:DATABASE_URL="<your Neon connection string>"
python manage.py migrate
python manage.py seed_data
python manage.py attach_product_images
Remove-Item Env:DATABASE_URL
```
2. `git add . ; git commit -m "Vercel backend" ; git push`
3. vercel.com > Add New > Project > import `vetri-bills`. Set **Root Directory** to `backend`. Framework preset: Other.
4. Environment variables: DJANGO_DEBUG=0, DJANGO_SECRET_KEY, DATABASE_URL, DJANGO_ALLOWED_HOSTS=.vercel.app,
   MOCK_PAYMENTS=1, RAZORPAY_KEY_ID=rzp_test_dummy, RAZORPAY_KEY_SECRET=dummy_secret, CRON_SECRET=<random text>.
5. Deploy, then open `https://<project>.vercel.app/api/products/`.

Notes: Vercel has no always-on process, so the daily expiry check runs from Vercel Cron (08:00 IST, see vercel.json).
Bill PDFs are rebuilt on demand. Pictures uploaded in admin are temporary: add permanent ones to backend/assets/product_images.
