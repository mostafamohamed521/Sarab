# Changelog — Full-Stack Audit

This document records every issue found and fixed during a complete audit of the Sarab
platform: architecture analysis, page-by-page verification, authentication/authorization,
security review, code organization, and a full read-through of every template and static
asset. Static analysis only — no network access was available during the audit, so the
project was never actually executed; every finding was traced by hand against the models,
views, serializers, URLs, and templates. **Run `python manage.py test` before deploying** to
get the one class of confirmation static analysis can't provide.

## OWASP Top 10 (2021) — systematic pass

A dedicated, category-by-category check, done in addition to (and cross-referenced against)
everything else in this document. Search was available for this pass, so A06 below reflects
real, current information rather than training-data recall.

| # | Category | Status |
|---|----------|--------|
| A01 | Broken Access Control | **Fixed.** See every IDOR/mass-assignment/privilege-escalation entry throughout this document. One item found *specifically* during this pass: custom Django Admin bulk actions (`orders/admin.py`, `reservations/admin.py`) didn't declare `allowed_permissions = ('change',)` — Django doesn't require "change" permission for custom actions automatically the way it does for the built-in `delete_selected`, so a hypothetical view-only admin account could otherwise trigger status changes. Fixed on every custom action. |
| A02 | Cryptographic Failures | **Clean.** Django's default PBKDF2 password hashing is untouched (no custom `PASSWORD_HASHERS`). `SECRET_KEY` is env-var based. `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/HSTS all enabled when `DEBUG=False`. No card data ever touches this server — Stripe handles it; only a non-sensitive PaymentIntent ID is stored. |
| A03 | Injection | **Clean.** Zero raw SQL, zero `eval`/`exec`, zero `pickle` anywhere in the codebase (checked again this pass, including every file added since the original sweep). No template auto-escaping is ever bypassed (`\|safe`/`mark_safe` are never used). |
| A04 | Insecure Design | **Fixed.** Coupon race condition, "only one default address" business rule, the broken address-form `country` field, reservation date validation — all covered above. Rate limiting added where none existed. |
| A05 | Security Misconfiguration | **Fixed.** `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS` moved off hardcoded values; production security headers (HSTS, `SECURE_SSL_REDIRECT`, `SECURE_REFERRER_POLICY`, `X-Content-Type-Options`) gated behind `DEBUG=False`; `SECURE_PROXY_SSL_HEADER` added for correct behavior behind Render's (or any PaaS) HTTPS-terminating proxy. No CORS package/config exists at all, which is the secure default here (this project has no legitimate cross-origin API consumer) — noted rather than "fixed" since there was nothing to misconfigure. |
| A06 | Vulnerable and Outdated Components | **Partially fixed — needs a decision only you can make.** See the dedicated section directly below; this is the most significant finding of this pass. |
| A07 | Identification and Authentication Failures | **Fixed.** Login rate limiting, "Remember me" actually wired up, Django's standard password validators untouched (4 validators, matches Django's recommended baseline), password reset uses Django's own signed-token flow (not custom). No MFA — a real enhancement opportunity, but a product decision/new feature, not a bug being fixed here. |
| A08 | Software and Data Integrity Failures | **Clean.** Stripe webhook signature verification was already correctly implemented (`stripe.Webhook.construct_event` with the signing secret) before this audit touched it — confirmed, not changed. No deserialization of untrusted data anywhere (`pickle`, `yaml.load`, etc. are never used). |
| A09 | Security Logging and Monitoring Failures | **Fixed.** No `LOGGING` configuration existed at all — added one (console handler; most hosts including Render capture stdout/stderr into their own aggregation, so this needs no extra infrastructure to be useful). Added explicit `logger.warning(...)` calls at the security decision points that matter: failed login attempts (`accounts/views.py`), every rate-limit trip across the whole app (centralized in `config/ratelimit.py::is_rate_limited`, so it automatically covers all seven rate-limited endpoints rather than needing a log call added at each one), and denied admin-dashboard access attempts (`config/admin_dashboard.py`). |
| A10 | Server-Side Request Forgery (SSRF) | **Not applicable.** The only outbound server-side HTTP calls anywhere in the codebase are to Stripe's fixed, hardcoded API domain (`stripe.PaymentIntent.create/retrieve`, `stripe.Webhook.construct_event`) — nothing in this app ever fetches a URL supplied by user input. |

### A06 in detail — Django 4.2 LTS reached end-of-life in April 2026

This is current information (verified via search, not training-data recall — my reliable
knowledge cutoff is January 2026, and this happened after that). **Django 4.2 LTS officially
stopped receiving security patches on April 7, 2026.** Any vulnerability discovered in Django
from that date forward will never be patched for the 4.2 series.

Six real vulnerabilities were patched in the run-up to and shortly after that EOL date,
including three **high-severity SQL injection** issues (`CVE-2026-1287`, `CVE-2026-1312`,
`CVE-2026-1207` — via `FilteredRelation`/`order_by()`/`annotate()` with crafted `**kwargs`,
and a PostGIS raster-lookup path) plus several denial-of-service issues. This project's code
doesn't happen to use the specific vulnerable patterns (`FilteredRelation`, dynamic
`**kwargs` passed to `annotate()`/`values()`/`order_by()` from user input, or PostGIS), so
these particular CVEs don't appear directly exploitable here — but that's incidental, not a
property of being on a patched version, since **4.2 is no longer receiving patches for
anything discovered next**.

What was fixed here, safely, without needing to test a major-version migration:
- `requirements.txt` now requires `Django>=4.2.30,<5.0` (was `>=4.2,<5.0`) — `4.2.30` is the
  final, fully-patched 4.2.x release covering every CVE found in this search. This is a
  same-series patch bump only — zero behavioral risk, safe to apply immediately.

What wasn't done, and shouldn't be done blindly: **upgrading to Django 5.2 LTS** (supported
until April 2028, the consistent recommendation across every current source found). This is
the right medium-term move, but a major-version Django upgrade can involve real breaking
changes (deprecated APIs removed, behavioral changes across versions), and this sandbox has no
way to install Django or run this project at all, let alone verify a migration didn't break
anything. Silently bumping the version pin without being able to test it would be irresponsible
regardless of how clean the rest of this audit is. If you want to pursue this, budget real
testing time against the actual test suite (`python manage.py test`) on the new version before
deploying it, and check `djangorestframework`/`Pillow`/`stripe` compatibility with Django 5.2
at the same time — DRF's own floor here (`>=3.14`) is already unaffected by any known CVE, so
that one's fine as-is either way.

## New — Deployment guidance for genuinely card-free free-tier hosting

Verified via search (current information, not training-data recall): Render's free tier
doesn't officially require a card, but has real, recent user reports of unexpected charges.
Added a full PythonAnywhere deployment walkthrough to `README.md` as the safer choice when
"zero payment details, no exceptions" genuinely matters — confirmed card-free across every
source checked, including PythonAnywhere's own documentation. Documented its two real
trade-offs honestly rather than glossing over them: free web apps expire after a month of
inactivity (needs a periodic manual renewal click), and outbound internet access is
allowlisted, so Stripe payments likely won't work without requesting that allowlisting or
upgrading — everything else in the app is unaffected either way.

## New — Admin dashboard overhaul

The Django Admin dashboard previously was just the bare, default app/model list with no
overview and no quick actions — every order or reservation had to be opened individually to
change its status, and there was no at-a-glance view of what needed attention.

- **Dashboard access restricted to `role=admin`** (see High section below) — this section
  assumes that's already in place.
- **New overview page** (`templates/admin/index.html`, stats built in
  `config/admin_dashboard.py::_build_dashboard_stats`, wired in via an `AdminSite.index()`
  override): today's order count and revenue, pending orders, pending reservations, unread
  contact messages, reviews awaiting approval, unavailable menu items (the closest real signal
  to "needs restocking/attention" — there's no literal stock-quantity field in this data model,
  so this deliberately isn't invented), and a recent-orders table. Every stat links straight to
  the pre-filtered list view for that item.
- **Bulk status-change actions on `OrderAdmin`**: mark selected orders Confirmed / Preparing /
  Ready / Out for Delivery / Delivered / Cancelled, plus a separate "mark as Paid" action for
  cash orders. Each goes through `order.save()` + `OrderStatusUpdate.objects.create(...)` —
  the same explicit pattern the customer-facing `cancel_order` view already uses — rather than
  a bare `queryset.update()`, which would silently skip the status-history record the
  customer's own order-tracking page depends on.
- **Bulk status-change actions on `ReservationAdmin`**: mark selected reservations Confirmed /
  Completed / No Show / Cancelled (reservations have no separate status-history model, so a
  plain bulk update is safe there).
- Added 3 regression tests covering the dashboard stats rendering and both sets of bulk
  actions actually changing the right records (and, for orders, actually creating the tracking
  entry).

## Critical

- **The "Add Address" and "Edit Address" pages in the customer profile could never actually
  save anything.** `AddressForm` requires `country` (the model field has no `blank=True`, so
  Django's ModelForm treats it as mandatory), but both hand-written HTML forms
  (`templates/accounts/addresses.html`, `templates/accounts/edit_address.html`) never included
  a `country` input at all. Every submission silently failed `form.is_valid()` and redirected
  back with a generic "please fill all required fields" message — with no `country` field
  visible anywhere on the page, there was no way for a user to ever get past this. There was
  also zero test coverage for `add_address`/`edit_address`/`delete_address`, which is why this
  went undetected. Fixed by adding a hidden `country` input to both forms — the same pattern
  the checkout page already uses for the same field — and added 6 regression tests covering
  add/edit/delete and the default-address exclusivity rule.
- **Payment bypass.** `/payments/success/<order_number>/` marked *any* order as paid on a bare
  GET request, with no verification a payment had actually happened. Now verifies the order's
  Stripe PaymentIntent before updating status; the signed Stripe webhook is the real source of
  truth, not the browser redirect.

## High — broken access control (IDOR)

- **Django Admin access only ever checked `is_staff`, ignoring this project's own
  customer/staff/admin `role` field entirely.** Any account with `is_staff=True` (however it
  got set) could log into `/admin/` and manage whatever models its permissions allowed —
  the `role` field existed but had never been wired to actual dashboard access (matching the
  broader finding, noted below, that `role` was decorative everywhere else too). Added
  `config/admin_dashboard.py::_admin_dashboard_only` (later moved out of `accounts/admin.py`
  into its own file — see the clean-code entry below), overriding `AdminSite.has_permission` so
  only `role=admin` accounts (or a superuser, kept as a safety net so
  `python manage.py createsuperuser` — which doesn't prompt for `role` — never locks its own
  creator out) can reach the dashboard at all; a `role=staff` account with `is_staff=True` is
  now bounced back to the login page instead. Also discovered while checking this: the README
  documented a seeded `admin@sarab.com` superuser that `seed_data.py` never actually created —
  fixed the seed script to create it for real (with `role=admin`) instead of leaving the docs
  wrong. Added 3 regression tests (`AdminSiteAccessTest`) covering admin/staff/customer access.

No ownership check on pages that took an ID straight from the URL, leaking another customer's
name/address/phone/email:
- `orders.order_success`, `orders.order_tracking`
- `payments.payment_stripe`, `payment_success`, `payment_failed`, `invoice`, `create_payment_intent`
- `reservations.reservation_confirmation` (for reservations tied to an account — guest
  reservations intentionally use the confirmation code alone as the credential, matching the
  existing guest-checkout design)

Added `orders/access.py::get_order_or_403` (owner, or the same browser session that just placed
a guest order) and applied it consistently.

Also fixed: **admin privilege escalation.** `CustomUserAdmin` inherited Django's stock
`UserAdmin` fieldsets unmodified, meaning any `is_staff` account with `Users → change`
permission could edit `is_superuser`, `is_staff`, `groups`, `user_permissions`, and `role` on
*any* account — including their own. Now only superusers can edit those fields; everyone else
with admin access can still manage ordinary account fields.

## High — mass assignment / privilege escalation (API)

- `OrderSerializer`: pricing (`subtotal`/`tax`/`discount`/`total`) and `payment_status`/`status`
  were client-writable — any authenticated user could PATCH their own order to `paid` or
  `$0`. Made read-only; added a real server-priced `create()` (the previous create path was
  also non-functional — nested `items` was read-only, so orders couldn't actually be placed
  through the API at all).
- `ReservationSerializer`: `status`/`confirmation_code` were client-writable — made read-only.
- `ReviewViewSet`: no object-level ownership check — any authenticated user could edit or
  delete anyone else's review by ID. Added `api/permissions.py::IsOwnerOrReadOnly`.

## Medium — unenforced business rules

- `Coupon.max_uses`/`min_order_amount` existed on the model but were never checked anywhere —
  a single-use coupon could be redeemed unlimited times. Added `Coupon.is_valid_for()`, used by
  both checkout and the "apply coupon" endpoint. Wrapped the actual redemption
  (`orders.place_order`) in `transaction.atomic()` with `select_for_update()` on the coupon row
  — without this, two simultaneous checkouts near a coupon's usage limit could both pass
  validation before either committed, over-redeeming it. (No-op on SQLite; takes effect on
  Postgres/MySQL in production.)
- `Address.is_default`: nothing enforced "only one default address per user" — a user could end
  up with several addresses simultaneously marked default, which also silently broke the
  checkout page's radio-button pre-selection. Fixed at the model layer (`Address.save()`), so
  every code path — views, admin, future API — gets the same guarantee. (An existing test,
  `test_only_one_default`, already expected this at the model level; it had never actually been
  implemented.)
- Reservation `date` had no server-side "not in the past" check (the HTML `min` attribute is
  client-side only) — added to both the web form and the API serializer; also added a `guests`
  upper bound to the API to match the web form's dropdown cap.

## Medium — input validation / error handling

- `reviews.add_review`: unguarded `int(rating)` → 500 on non-numeric input → now validated,
  returns 400.
- `cart_add`/`cart_update`: unguarded `int(quantity)`, no upper bound → validated + capped at 50.
- `cms_pages.contact_submit`: **leaked raw exception text to the client**
  (`except Exception as e: ... str(e)`) — a classic information-disclosure bug. Rewritten to
  fail safely with generic messages and field-length truncation.

## Medium — no rate limiting anywhere

Added a small dependency-free limiter (`config/ratelimit.py`, built on Django's cache
framework) to `login_view` (10 failed attempts/5min — only failures count, so a correct login
is never penalized), `register_view`, the password-reset request view, `newsletter_subscribe`,
`contact_submit`, `make_reservation`, and `place_order` (10–20/hour). Added DRF's built-in
`AnonRateThrottle`/`UserRateThrottle` (100/min anon, 300/min authenticated) across the whole
`/api/v1/` surface.

## Medium — performance (N+1 queries)

`average_rating`/`review_count`/`item_count` cost 2+ extra queries *per row* on the homepage,
full menu, wishlist, item detail, order history, and their API equivalents. Fixed via queryset
annotation with a backward-compatible property fallback (nothing else had to change), plus
`select_related`/`prefetch_related` for tags, review authors, and order items.

## Medium — broken/misleading page content

Found by reading every one of the 34 templates in full, not just structurally:

- **`Category.get_absolute_url()`** pointed at a URL name (`menu_category`) that didn't exist
  anywhere — Django Admin's automatic "View on site" button would 500 for any category. Found
  via a whole-project URL-reference graph (every `reverse()`/`redirect()`/`{% url %}` validated
  against every defined route, both directions). Fixed to point at the real category-filtered
  menu view.
- **Item detail star ratings always rendered empty**, regardless of the actual average rating.
  `{% if forloop.counter <= item.average_rating|floatformat:'0' %}` compares an int to a string
  (`floatformat` always returns a string), which always raises `TypeError` — verified against
  Django's own source/issue tracker that `{% if %}` silently swallows this to `False` rather
  than crashing the page, which is why this went unnoticed. Fixed to compare the numeric value
  directly.
- **"Add $X more for free delivery" always showed the flat delivery fee ($3.99)**, never the
  actual amount needed to reach the $30 threshold — factually wrong for any subtotal other than
  one coincidentally close to the fee amount. Added `Cart.get_remaining_for_free_delivery()`.
- **Applying a coupon updated the discount line but never recalculated the visible total** on
  the cart and checkout pages — numbers didn't add up on screen (the order actually placed was
  always correctly discounted server-side; this was display-only). Fixed both pages.
- **The "Remember me" login checkbox did nothing** — every login silently got Django's default
  2-week session regardless of the checkbox. Wired to `request.session.set_expiry(0)`.
- **`order_success.html` showed a hardcoded "~30 minutes"** instead of the real
  `estimated_delivery` timestamp the model already stores, inconsistent with the tracking page,
  which showed it correctly. Fixed to use the real value with the old text as a fallback.
- **`payments/success.html` always showed a "Paid" badge**, which became actively misleading
  once `payment_success` (see Critical, above) stopped assuming success just from a browser
  redirect — a user could land there before verification completed. Fixed to reflect the real
  `payment_status`, with an honest "Confirming Your Payment" state for the unconfirmed case.
- **The reservation form discarded every specific server error** (including the new
  rate-limit/date-validation messages above), always showing a generic "check your form" toast.
  Fixed to surface the real message.
- **The contact form showed a false "Message Sent!" success box even when the submission
  failed** (rate-limited, invalid email) — actively told the user their message was received
  when it wasn't. Fixed to only show success on an actual success response.
- **The cart sidebar's own quantity +/- buttons never refreshed the Subtotal/Tax/Total shown
  right below them** — went stale immediately. Matched the pattern the full cart page already
  uses correctly (reload after mutation) instead of inventing a second, partial-update path.
- **The global "Add to Cart"/"Wishlist" click handlers had no error handling at all** — an
  error response would still show the success checkmark animation, and a non-JSON error
  response (e.g. a 404 page) threw an uncaught `SyntaxError` with zero user feedback. Added
  proper status checks and `.catch()`.
- **CSS bug affecting three pages (Contact, About, and the homepage's own info cards):**
  `.fcard` was defined twice in `style.css` for two unrelated purposes — small floating badges
  over the homepage hero (`position: absolute; display: flex`) and vertical icon+text info
  cards (Visit Us / Call Us / etc.). The second definition never reset the first's positioning
  properties, so every plain info card was pulled out of the page's normal flow and its
  icon/heading/text were squashed into a horizontal row instead of stacking vertically. Fixed
  by resetting the conflicting properties in the info-card rule and making the hero-badge
  variant (`.fcard.fc1/.fc2/.fc3`) fully self-contained so it's immune to either rule.

## Low — hardening & cleanup

- **Deleted 12 dead files**: 9 per-app `tests.py` stubs (`startapp` boilerplate — the real,
  central test suite has always lived in the root `tests.py`, so these were pure noise with
  zero content) and 3 per-app `admin.py` stubs (`api`, `cart`, `payments` — none of these apps
  have models needing registration, so these were an unused `admin` import and a comment,
  nothing else).
- **`reviews/admin.py` imported `Wishlist` but never registered it** — staff had no way to see
  which items customers had wishlisted anywhere in the admin. Registered `WishlistAdmin`
  (the import already implied this was intended and just never finished).
- **Separated two unrelated concerns that had been living in the same file.** The site-wide
  admin dashboard customization (access gate + stats overview, added earlier in this audit) was
  tacked onto `accounts/admin.py`, which otherwise is — and should only be — about registering
  `CustomUser`/`Address`/`NewsletterSubscriber`. Moved the site-wide pieces to their own
  `config/admin_dashboard.py` (imported once, for its side effects, from `accounts/admin.py`);
  cut that file from 121 lines to 41 and made both files' actual purpose unambiguous from their
  contents alone.
- **Extracted `orders/views.py::_resolve_coupon()`** out of `place_order`, which had grown to
  ~85 lines mixing request parsing, coupon validation, order creation, and payment-method
  branching in one function. The coupon-lookup-and-validate step is now a small, independently
  readable unit; behavior is unchanged (still runs inside the same `select_for_update()`
  transaction).
- Hardcoded `SECRET_KEY`/`DEBUG=True`/`ALLOWED_HOSTS=['*']`/Stripe keys moved to environment
  variables (identical dev defaults, so local `runserver` is unaffected) + `.env.example` +
  production security headers gated behind `DEBUG=False`.
- 5MB size validator added to `CustomUser.avatar` — the one customer-facing (not staff-only)
  upload field; no cap existed before.
- Deleted a dead duplicate `project/` Django scaffold (leftover `startproject` output, wired
  into nothing).
- Removed unused `django-extensions`/`django-filter` dependencies and roughly a dozen dead
  imports across `accounts`, `api`, `cart`, `menu`, `payments`, `reviews`, plus an unused `Tag`
  import in the root `tests.py`.
- Fixed a hardcoded Stripe publishable key in `orders/views.py` duplicating (and able to drift
  from) `settings.STRIPE_PUBLISHABLE_KEY`.
- Removed a redundant always-true `hasattr(user, 'order_set')` conditional in `profile_view`.
- **`static/js/main.js` contained leftover demo-template code** referencing a `#resBtn` element
  that no longer exists (superseded by a real, backend-wired reservation handler in
  `home.html`'s own inline script). That crashed on page load and silently killed every line of
  JS after it in the same file — including the newsletter button (genuinely dead — clicking it
  did nothing) and the testimonials carousel/countdown timer. Removing the crash naively would
  have just unblocked more leftover, now-duplicate code (a second Swiper instance, a second
  gallery index, a fake local-only newsletter handler racing the real one) — removed the dead
  blocks entirely rather than patch around them.

## Confirmed correct — no changes needed

A non-exhaustive list of things specifically checked and found already correct, to avoid
re-litigating them: cart pricing is always server-computed from the current `MenuItem.price`,
never trusted from the client; CSRF is correctly wired everywhere; no raw SQL, `eval`/`exec`,
or `pickle` anywhere in the codebase; no XSS surface (`|safe`/`mark_safe` are never used); every
`render()` call and every `{% extends %}`/`{% include %}` across all 34 templates resolves to a
real file; every template's Django tags are properly balanced; all 33 `{% static %}` references
resolve to real files; all inline `<script>` blocks (and `static/js/main.js`) are syntactically
valid JavaScript; Django Admin's `list_display`/`list_filter`/`search_fields`/inlines are all
valid across every registered model.

## Explicitly not built (product decisions, not bugs)

- A customer-facing staff dashboard beyond Django Admin. `CustomUser.role`/`is_admin_user`/
  `is_staff_user` exist but are enforced nowhere outside unit tests — there's no partial or
  broken version of this to complete, and the README documents "Admin (Django Admin)" as the
  intended design.
- Custom-themed 404/500 error pages — currently Django's plain defaults, which are safe (no
  information leakage with `DEBUG=False`) but unbranded.

## Self-correction

- Four IDOR regression tests added earlier in this audit (`make_user(email='...',
  username='...')`) passed `username` both explicitly and implicitly through `**kwargs` to the
  `make_user()` test helper, which already sets `username=email` internally — this raised a
  `TypeError` at call time rather than the intended assertion. Caught while adding the address
  tests above (this project's sandbox has no way to actually run Django, so these went
  unverified until traced by hand) and fixed across all four occurrences.
