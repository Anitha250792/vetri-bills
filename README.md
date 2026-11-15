# Vetri Bills

E-commerce billing app: one Django backend, used by a mobile app and a website (Expo, added on Day 4).
Main feature: notify when product batches are about to expire or have expired, and when stock is low.

## Run the backend (Day 1)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional; without POSTGRES_DB the app uses SQLite
python manage.py migrate
python manage.py seed_data      # 30 sample products, admin + demo users
python manage.py runserver
```

To use PostgreSQL: `docker compose up -d` (from the project root), keep the `POSTGRES_*` lines in `.env`, then run `migrate` and `seed_data` again.

| What | URL |
| --- | --- |
| Admin dashboard (shop owner) | http://localhost:8000/admin/ |
| API docs (Swagger) | http://localhost:8000/api/docs/ |

Seed logins: `admin / Admin@12345` and `demo / Demo@12345`. Change them before deploying.

## Day 1 endpoints

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/auth/register/` | Always creates a customer |
| POST | `/api/auth/login/` | Username or email + password; returns `access`, `refresh`, `user` |
| POST | `/api/auth/token/refresh/` | |
| GET / PATCH | `/api/auth/profile/` | Bearer token required |
| POST | `/api/auth/device-token/` | Saves the Expo push token |
| GET | `/api/categories/` | With product counts |
| GET | `/api/products/` | `search`, `category` (slug), `min_price`, `max_price`, `in_stock`, `ordering`, `page` (12 per page) |
| GET | `/api/products/{id}/` | Includes sellable batches and expiry dates |

## Day 2 endpoints (all need `Authorization: Bearer <access token>`)

| Method | Path | Notes |
| --- | --- | --- |
| GET / DELETE | `/api/cart/` | View the cart / empty it |
| POST | `/api/cart/items/` | `{product_id, quantity}`; quantities add up; refuses more than the stock |
| PATCH / DELETE | `/api/cart/items/{product_id}/` | Set quantity / remove |
| GET | `/api/wishlist/` | |
| POST | `/api/wishlist/toggle/` | `{product_id}`; adds, or removes if already there |
| POST | `/api/checkout/` | `{shipping_address?}`; creates the order and the Razorpay order |
| POST | `/api/payments/verify/` | `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`; takes stock, creates the bill, empties the cart |
| POST | `/api/payments/mock-pay/` | Development only (`MOCK_PAYMENTS=1`): returns a valid payment id and signature |
| GET | `/api/orders/`, `/api/orders/{id}/` | Order history |
| GET | `/api/bills/` | The customer's bills |
| GET | `/api/bills/{id}/download/` | The bill as a PDF |

### Try the purchase flow without an app

Open http://127.0.0.1:8000/api/docs/, call **login**, click **Authorize** and paste the `access` token, then run:
`cart/items` (add a product) → `checkout` → `payments/mock-pay` (paste the `razorpay_order_id`) → `payments/verify` (paste the three values) → `bills/{id}/download`.

### Payments

`MOCK_PAYMENTS=1` (the default) never contacts Razorpay, so dummy keys work. To use Razorpay test mode later, put your `rzp_test_` keys in `.env` and set `MOCK_PAYMENTS=0`. The server always checks the payment signature itself.

## Day 3: expiry and low-stock alerts

Who is told: every active user with the **admin** role (superusers are admins automatically). Customers never get these.

| Alert | When it is created |
| --- | --- |
| Expiring soon | A batch with stock left expires within `EXPIRY_WARNING_DAYS` (default 7), including today |
| Expired | A batch with stock left has passed its expiry date. Expired units stop counting as stock |
| Low stock | A product's stock is at or below its `low_stock_threshold`, or is 0 |

Each alert is created once per batch or product (low stock again only after a restock), so running the check twice never doubles up. Alerts appear **straight away** after a sale or when you add or edit a batch in the admin, and also in the **daily check**.

```bash
python manage.py check_expiry_stock   # run the daily check once, now
python manage.py run_scheduler        # keep running; checks every day at 08:00 (SCHEDULE_HOUR / SCHEDULE_MINUTE)
python manage.py run_scheduler --now  # same, and also checks immediately
```

You can also run `check_expiry_stock` from Windows Task Scheduler, cron, or your host's cron job instead of `run_scheduler`.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/notifications/` | Your alerts, newest first. Filters: `is_read=false`, `type=expiry_soon / expired / low_stock` |
| GET | `/api/notifications/unread-count/` | `{"unread": 3}` for the bell badge |
| POST | `/api/notifications/{id}/read/` | Mark one as read |
| POST | `/api/notifications/read-all/` | Mark all as read |
| GET | `/api/admin/expiry-report/` | Admin only. `expired`, `expiring_soon` (`?days=30` to widen), `low_stock`, plus counts |

**Push notifications (mobile):** the app saves its Expo push token with `POST /api/auth/device-token/`. Admins' devices then get a push for each new alert, and one summary push from the daily check. Set `PUSH_ENABLED=0` to switch pushes off. A failed push never blocks a sale.

**Test it with the demo data:** `python manage.py seed_data` creates 2 expired batches, several expiring soon and 3 low-stock products. Log in to `/admin/` as `admin`, open Notifications, and call `/api/admin/expiry-report/` from the API docs page.
To test by hand, edit a batch's expiry date to tomorrow in the admin and save: the alert appears immediately.

## Notes

- Stock is taken when payment succeeds, from the batch that expires first. If an item sells out between checkout and payment, the order is marked `failed` and the payment `needs_refund`.
- Prices include tax (like an MRP tag); the bill splits out the tax.

- Stock is the sum of batches that have not expired; expired units are not sellable.
- `OrderItem` copies price and tax at purchase time so old bills never change.
- Tests: `python manage.py test`

## Day 4: Mobile + web app
See `app/README.md`. Run backend + `cd app; npm install; npx expo start --web`.
Test login: customer `demo` / `Demo@12345`, admin `admin` / `Admin@12345`.

## Day 4b: product photos + premium bill
- `python manage.py attach_product_images`: bundled pictures (offline).
- `python manage.py fetch_product_images`: real photos from Wikipedia (needs internet; `--force` to redo).
- Replace any picture by hand in Django admin > Products > Image.
- Bill PDF is now a premium tax invoice (header band, PAID badge, QR, CGST/SGST split).
