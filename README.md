# Sarab — Django Food & Restaurant Platform

A complete Django e-commerce and restaurant management platform: online ordering, table
reservations, a customer account system, reviews/wishlist, Stripe payments, and a REST API —
all backed by Django Admin for staff.

This codebase has been through a full security, integrity, and code-quality audit. See
[`CHANGELOG.md`](CHANGELOG.md) for the complete list of what was reviewed and fixed — including
a systematic OWASP Top 10 pass and an important, current finding about Django's own support
lifecycle (Django 4.2 LTS reached end-of-life in April 2026; see `CHANGELOG.md`'s A06 section
before deploying this anywhere long-term). The sections below reflect the **current, audited**
state of the project.

## Quick Start (local development)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional for local dev) Set environment variables — see .env.example
#    for the full list. settings.py reads these directly from the process
#    environment; there's no python-dotenv dependency, so a .env file by
#    itself does nothing unless your shell/host loads it for you, e.g.:
export $(cat .env.example | grep -v '^#' | xargs)   # or set them however your shell/host prefers

# 3. Apply migrations
python manage.py migrate

# 4. Seed sample data (categories, menu items, users, coupons, reservations...)
python manage.py seed_data

# 5. Create your own admin superuser (or use the seeded admin@sarab.com / admin123)
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

Without those variables set, the app falls back to safe local-development
defaults (`DEBUG=True`, a placeholder `SECRET_KEY`, `ALLOWED_HOSTS=*`, console email backend,
placeholder Stripe test keys) — so the Quick Start above works out of the box. **None of those
defaults are safe for a real deployment** — see [Deploying to Production](#deploying-to-production).

## Access Points

| URL | Description |
|-----|-------------|
| `http://localhost:8000/` | Homepage |
| `http://localhost:8000/menu/` | Full Menu |
| `http://localhost:8000/reservations/` | Table Reservations |
| `http://localhost:8000/cart/` | Shopping Cart |
| `http://localhost:8000/orders/checkout/` | Checkout |
| `http://localhost:8000/accounts/login/` | Login |
| `http://localhost:8000/accounts/register/` | Register |
| `http://localhost:8000/admin/` | Django Admin |
| `http://localhost:8000/api/v1/` | REST API |

## Seeded Accounts (local/dev data only — `seed_data` command)

| Role | Email | Password | Django Admin access |
|------|-------|----------|----------------------|
| Admin | admin@sarab.com | admin123 | ✅ Yes |
| Staff | staff@sarab.com | sarab2026 | ❌ No — see below |
| Customer | customer@sarab.com | sarab2026 | ❌ No |
| Customer | jane@sarab.com | sarab2026 | ❌ No |

These are seed-script credentials for local development only. Never seed this data, or leave
these accounts active, on a real deployment.

**Django Admin (`/admin/`) is restricted to `role=admin` accounts only** (or any superuser, as
a safety net so `python manage.py createsuperuser` always works even though it doesn't prompt
for `role`). Having `is_staff=True` alone is *not* enough — the seeded `staff@sarab.com` account
demonstrates this: even if it were granted `is_staff=True`, its `role` is `staff`, so it's
bounced back to the login page rather than reaching the dashboard. See
`config/admin_dashboard.py::_admin_dashboard_only`.

## Sample Promo Codes (seeded)

| Code | Discount |
|------|----------|
| `WELCOME15` | 15% off any order |
| `SAVE5` | $5 off orders over $20 |
| `FRIDAY20` | 20% off orders over $30, limited uses |

## Architecture

```
sarab_project/
├── config/              Settings, root URLs, the rate limiter, and admin dashboard customization
├── accounts/            Custom user model, auth, addresses
├── menu/                Categories, menu items, variants, addons
├── cart/                Session-based cart engine
├── orders/              Orders, order items, coupons, status tracking
├── reservations/        Table reservations with confirmation codes
├── reviews/             Item reviews & wishlist
├── payments/            Stripe integration, invoices
├── cms_pages/           About, Contact, Blog, FAQ, legal pages
├── api/                 REST API (DRF) — all resources
├── templates/           All HTML templates (Django)
├── static/               CSS, JS, images
├── tests.py              124 automated tests
├── .env.example           Documented environment variables for deployment
├── CHANGELOG.md           Full audit trail of what was reviewed and fixed
├── render.yaml            Render Blueprint (one-click deploy config)
├── build.sh               Render build script (install, collectstatic, migrate)
└── requirements.txt
```

## REST API Endpoints

All endpoints are versioned under `/api/v1/` and rate-limited (100 requests/minute for
anonymous clients, 300/minute for authenticated users).

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/categories/` | Public | All active menu categories |
| GET | `/api/v1/menu/` | Public | Menu items (search, filter, order) |
| GET | `/api/v1/menu/{slug}/` | Public | Single menu item detail |
| GET, POST | `/api/v1/orders/` | Required | List/create your own orders — pricing is always computed server-side from live menu-item prices |
| GET, POST | `/api/v1/reservations/` | Public read / auth to create | List/create your own reservations |
| GET, POST | `/api/v1/reviews/` | Public read / auth to create | Approved reviews; only the review's author can edit/delete it |

Query parameters:
- `?search=burger` — full-text search
- `?category=burgers` — filter by category slug
- `?featured=true` — featured items only
- `?ordering=price` or `?ordering=-price` — sort by price

## Features

### Customer
- Account registration & login with email, optional "remember me" session
- Profile management & avatar upload (5MB limit)
- Saved delivery addresses (multiple, with a single enforced default)
- Full menu browsing with category filters & live search
- Real-time cart sidebar with quantity controls
- Multi-step checkout with saved address selection and coupon codes
- Order placement (cash / Stripe / PayPal)
- Live order tracking with a status timeline
- Order history, detail view, and printable invoice
- Table reservation with a confirmation code
- Reservation history & cancellation
- Wishlist (toggle heart on any item)
- Item reviews with star ratings
- Password reset via email
- Newsletter subscription

### Admin (Django Admin)
- Dashboard access is restricted to `role=admin` accounts (or superusers) — `is_staff=True`
  alone is no longer sufficient
- **Dashboard overview page**: today's orders/revenue, pending orders, pending reservations,
  unread messages, reviews awaiting approval, unavailable menu items, and a recent-orders table
  — every stat links to the relevant filtered list
- **Bulk order actions**: change status (Confirmed/Preparing/Ready/Out for Delivery/Delivered/
  Cancelled) or mark paid for multiple selected orders at once, without opening each one
- **Bulk reservation actions**: Confirmed/Completed/No Show/Cancelled for multiple selected
  reservations at once
- User management — role/staff/superuser fields are editable by superusers only
- Menu item CRUD with inline variations & addons
- Category management with ordering
- Reservation & table management
- Coupon management (usage caps and minimum-order rules are enforced)
- Blog post & FAQ management
- Contact message inbox
- Review moderation

### Pages
Home · Full Menu · Item Detail · Cart · Checkout · Order Success/Tracking/History/Detail ·
Invoice · Table Reservation & History · Login/Register/Password Reset · Profile/Addresses/Wishlist
· About/Contact/FAQ/Blog/Legal pages — 50 routes total, all verified to render and connect to a
real backend (see `CHANGELOG.md`).

## Running Tests

```bash
python manage.py test tests -v 2
# Expected: 124 tests, all OK
```

## Configuration (environment variables)

All secrets and environment-specific settings are read from real environment variables with
safe local-dev fallbacks — nothing is hardcoded in `config/settings.py` anymore.
`.env.example` documents every variable `settings.py` reads; export them however your
shell or hosting platform expects (there's no `python-dotenv` dependency here, so a `.env`
file on its own is inert unless something loads it into the environment first):

```
DJANGO_SECRET_KEY=<long random value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

Set the Stripe webhook secret to match what Stripe's dashboard gives you once the webhook
endpoint (`/payments/webhook/`) is registered against your live domain — this is what makes
`payment_status` transitions to `paid` trustworthy rather than just trusting the browser redirect.

## Deploying to Production

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Set a strong, random `DJANGO_SECRET_KEY` (never reuse the local-dev default)
- [ ] Set `DJANGO_ALLOWED_HOSTS` to your real domain(s) — not `*`
- [ ] Point `EMAIL_BACKEND` at a real SMTP provider (it's the console backend by default —
      password reset emails currently only print to the terminal)
- [ ] Set `DATABASE_URL` to a real PostgreSQL instance (see [Deploying to Render](#deploying-to-render-free-tier)
      below) — `config/settings.py` uses it automatically when present, falling back to SQLite otherwise
- [ ] Configure S3 (or similar) for `MEDIA_ROOT` if you expect real traffic/uploads — static
      files (CSS/JS/images) are already handled by WhiteNoise and need no extra setup, but
      user-uploaded media (avatars, menu photos) still writes to local disk, which most PaaS
      free tiers wipe on every redeploy
- [ ] Set real Stripe keys and webhook secret (see above)
- [ ] Run `python manage.py makemigrations accounts && python manage.py migrate` (picks up the
      avatar upload size validator — a model-level change, not a schema change, but Django will
      flag it as pending until this runs)
- [ ] Run `python manage.py collectstatic`
- [ ] Point `CACHES` at Redis/Memcached if running multiple app workers — the rate limiter
      (`config/ratelimit.py`) needs a cache shared across processes to work correctly; the
      in-memory default only protects a single process
- [ ] Serve with gunicorn (already in `requirements.txt`) behind your platform's HTTPS proxy
- [ ] Run the full test suite (`python manage.py test`) against the production settings profile
      before going live

## Deploying to Render (free tier)

The project is pre-configured for Render — `gunicorn`, `psycopg2-binary`, `dj-database-url`,
and `whitenoise` are already in `requirements.txt`, and `config/settings.py` picks up Render's
`DATABASE_URL`/`RENDER_EXTERNAL_HOSTNAME` automatically.

**Option A — one-click via Blueprint (`render.yaml`):**
1. Push this repo to GitHub.
2. On Render: **New → Blueprint**, point it at your repo. `render.yaml` provisions the free
   Postgres database and the web service together, and generates a random `DJANGO_SECRET_KEY`
   for you.
3. After the first deploy, add `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, and
   `STRIPE_WEBHOOK_SECRET` in the service's **Environment** tab — these are real secrets and
   deliberately aren't in `render.yaml`.

**Option B — manual setup:**
1. On Render: **New → PostgreSQL** (free plan) → note the generated **Internal Database URL**.
2. **New → Web Service**, connect your repo.
   - Build Command: `bash build.sh`
   - Start Command: `gunicorn config.wsgi:application`
3. Add environment variables: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` (any long random
   string), `DATABASE_URL` (the Internal Database URL from step 1), plus the three Stripe
   variables above.
4. Deploy. Render assigns a `*.onrender.com` URL and sets `RENDER_EXTERNAL_HOSTNAME`
   automatically — `settings.py` adds it to `ALLOWED_HOSTS` for you.

**Known limits of Render's free tier:** the service sleeps after 15 minutes with no traffic
(the first request after that takes a few seconds to wake it up), and the free Postgres
database expires after 90 days unless upgraded. Fine for testing/demos; budget for the paid
tier before relying on this for real traffic. ⚠️ Render's own free-tier terms don't require a
card, but there are user reports of unexpected charges on "free" accounts — if you want a
platform with a cleaner zero-card track record, use PythonAnywhere below instead.

## Deploying to PythonAnywhere (free tier, genuinely no card required)

Unlike Render, PythonAnywhere's free tier has no `render.yaml`-style one-click flow — you set
it up through their web dashboard and a browser-based Bash console. It also doesn't use
gunicorn or Postgres at all; it serves Django through its own WSGI infrastructure, and the
project's default SQLite database works as-is (new free accounts don't get MySQL access
either, so there's nothing extra to configure there).

1. Sign up at pythonanywhere.com (free "Beginner" account — no payment details asked for).
2. Open a **Bash console** from the dashboard and clone your repo:
   ```bash
   git clone <your-repo-url> sarab
   cd sarab
   python3.11 -m venv venv   # use whichever Python 3.x version PythonAnywhere currently
                              # offers when you sign up — check the Web tab's version
                              # dropdown in step 3 and match it here
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
3. Go to the **Web** tab → **Add a new web app** → choose **Manual configuration** → pick the
   same Python version as your virtualenv.
4. Set the **Virtualenv** path to `/home/<your-username>/sarab/venv`.
5. Open the generated **WSGI configuration file** (linked from the Web tab) and replace its
   contents with:
   ```python
   import os, sys
   sys.path.insert(0, '/home/<your-username>/sarab')
   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
   os.environ['DJANGO_DEBUG'] = 'False'
   os.environ['DJANGO_SECRET_KEY'] = '<a long random string — generate one, don\'t reuse the dev default>'
   os.environ['DJANGO_ALLOWED_HOSTS'] = '<your-username>.pythonanywhere.com'
   # Stripe (optional — see the note below on outbound requests first)
   os.environ['STRIPE_PUBLISHABLE_KEY'] = 'pk_...'
   os.environ['STRIPE_SECRET_KEY'] = 'sk_...'
   os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_...'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
6. Back in the **Web** tab, under **Static files**, add two mappings:
   - URL `/static/` → Directory `/home/<your-username>/sarab/staticfiles`
   - URL `/media/` → Directory `/home/<your-username>/sarab/media`
7. Click the big green **Reload** button. Your site is live at
   `https://<your-username>.pythonanywhere.com`.

**Two honest trade-offs, not present on Render:**
- Free-tier web apps expire after **1 month** of inactivity — log into the dashboard and click
  "Run until 3 months from today" periodically to keep it alive. This project's account
  cleanup/rate-limiting logic is unaffected either way; this is purely a PythonAnywhere hosting
  quirk.
- Free accounts have **restricted outbound internet access** (only a small allowlist of
  domains). Stripe's API is very likely not on that allowlist by default, so payments may not
  work until you either request it be whitelisted (PythonAnywhere's support has historically
  granted this for free accounts on request) or upgrade to a paid plan (which grants
  unrestricted outbound access). Everything else in the app — browsing, cart, reservations,
  reviews, the admin dashboard — works fully regardless, since none of it makes outbound calls.
