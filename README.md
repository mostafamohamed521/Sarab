# Sarab — Django Food & Restaurant Platform

A complete, production-ready Django e-commerce and restaurant management platform.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Seed sample data
python manage.py seed_data

# Create admin superuser (or use seeded admin@sarab.com / admin123)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

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

## Admin Credentials (seeded)
- **Email:** admin@sarab.com
- **Password:** admin123

## Sample Customer Accounts
- customer@sarab.com / sarab2026
- jane@sarab.com / sarab2026

## Sample Promo Codes
- `WELCOME15` — 15% off any order
- `SAVE5` — $5 off orders over $20
- `FRIDAY20` — 20% off orders over $30

## Architecture

```
sarab_project/
├── config/              Django project settings & root URLs
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
├── static/              CSS, JS, images (from original template)
├── tests.py             109 automated tests
└── requirements.txt
```

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/categories/` | All menu categories |
| GET | `/api/v1/menu/` | All menu items (search, filter, order) |
| GET | `/api/v1/menu/{slug}/` | Single menu item detail |
| GET/POST | `/api/v1/orders/` | Customer orders (auth required) |
| GET/POST | `/api/v1/reservations/` | Reservations |
| GET | `/api/v1/reviews/` | Approved reviews |

Query parameters:
- `?search=burger` — full-text search
- `?category=burgers` — filter by category slug
- `?featured=true` — featured items only
- `?ordering=price` or `?ordering=-price` — sort by price

## Features

### Customer
- Account registration & login with email
- Profile management & avatar upload
- Saved delivery addresses (multiple, default)
- Full browsing menu with category filters & search
- Real-time cart sidebar with quantity controls
- Multi-step checkout with saved address selection
- Coupon/promo code application
- Order placement (cash / Stripe / PayPal)
- Live order tracking with status timeline
- Order history & detail views
- Printable invoice per order
- Table reservation with confirmation code
- Reservation history & cancellation
- Wishlist (toggle heart on any item)
- Item reviews with star ratings
- Password reset via email
- Newsletter subscription

### Admin (Django Admin)
- Full user management
- Menu item CRUD with inline variations & addons
- Category management with ordering
- Order management with status updates
- Reservation management
- Coupon management
- Blog post management
- FAQ management
- Contact message inbox
- Review moderation

### Pages
- Home (hero, categories, menu, gallery, chefs, hours, testimonials, reservation form, blog, newsletter, contact)
- Full Menu (filter by category, search, expandable item cards)
- Item Detail (gallery, add to cart, reviews, related items)
- Cart (full cart management, coupon application)
- Checkout (saved addresses, payment method selection)
- Order Success, Tracking, History, Detail
- Invoice (print-ready)
- Table Reservation (form + confirmation)
- Reservation History
- Login / Register / Forgot Password / Reset Password
- Profile / Edit Profile / Addresses / Wishlist
- About Us / Contact / FAQ / Blog / Legal pages

## Running Tests

```bash
python manage.py test tests -v 2
# Expected: 109 tests, all OK
```

## Stripe Integration

Set these in `config/settings.py`:
```python
STRIPE_PUBLISHABLE_KEY = 'pk_live_...'
STRIPE_SECRET_KEY = 'sk_live_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'
```

## Production Checklist

- [ ] Set `DEBUG = False`
- [ ] Set a strong `SECRET_KEY`
- [ ] Configure real email backend (SMTP/SendGrid)
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure AWS S3 or similar for media files
- [ ] Set real Stripe keys
- [ ] Run `python manage.py collectstatic`
- [ ] Use gunicorn + nginx for serving
