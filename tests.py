"""
Sarab Food Platform - Full Test Suite
Covers: Models, Views, Forms, API, Cart Logic
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
import json

from accounts.models import CustomUser, Address, NewsletterSubscriber
from menu.models import Category, MenuItem, ContactMessage
from cart.cart import Cart
from orders.models import Order, OrderItem, OrderStatusUpdate, Coupon
from reservations.models import Reservation, Table
from reviews.models import Review, Wishlist
from cms_pages.models import FAQ, BlogPost


# ─── Helper factories ────────────────────────────────────────────────────────

def make_user(email='test@sarab.com', password='testpass123', **kwargs):
    return CustomUser.objects.create_user(
        email=email, username=email, password=password,
        first_name='Test', last_name='User', **kwargs
    )


def make_category(name='Burgers', slug='burgers'):
    return Category.objects.get_or_create(
        slug=slug, defaults={'name': name, 'is_active': True, 'order': 1}
    )[0]


def make_item(name='Classic Burger', price='12.99', category=None, **kwargs):
    if category is None:
        category = make_category()
    from django.utils.text import slugify
    return MenuItem.objects.get_or_create(
        slug=slugify(name),
        defaults={
            'name': name, 'category': category,
            'price': Decimal(price),
            'description': 'A delicious test burger.',
            'short_description': 'Test burger.',
            'is_available': True,
            **kwargs
        }
    )[0]


def make_order(user=None, **kwargs):
    return Order.objects.create(
        user=user,
        full_name='John Doe', email='john@test.com', phone='555-0100',
        street_address='123 Test St', city='New York', state='NY',
        zip_code='10001', country='United States',
        subtotal=Decimal('20.00'), tax=Decimal('1.60'),
        delivery_fee=Decimal('3.99'), discount=Decimal('0.00'),
        total=Decimal('25.59'),
        payment_method='cash',
        **kwargs
    )


# ─── Account Models ───────────────────────────────────────────────────────────

class CustomUserModelTest(TestCase):
    def test_create_user(self):
        u = make_user()
        self.assertEqual(u.email, 'test@sarab.com')
        self.assertEqual(u.role, CustomUser.ROLE_CUSTOMER)
        self.assertTrue(u.check_password('testpass123'))

    def test_superuser_is_admin(self):
        u = CustomUser.objects.create_superuser(
            email='su@sarab.com', username='su@sarab.com', password='pass123'
        )
        self.assertTrue(u.is_admin_user)
        self.assertTrue(u.is_superuser)

    def test_get_full_name(self):
        u = make_user()
        self.assertEqual(u.get_full_name(), 'Test User')

    def test_email_is_username_field(self):
        self.assertEqual(CustomUser.USERNAME_FIELD, 'email')

    def test_role_choices(self):
        u = make_user(role=CustomUser.ROLE_STAFF)
        self.assertTrue(u.is_staff_user)

    def test_str(self):
        u = make_user()
        self.assertEqual(str(u), 'test@sarab.com')


class AddressModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_create_address(self):
        addr = Address.objects.create(
            user=self.user, label='home', full_name='Test User',
            phone='555-0100', street_address='42 Flavor St',
            city='New York', state='NY', zip_code='10001',
            country='United States', is_default=True
        )
        self.assertEqual(str(addr), 'home - 42 Flavor St, New York')

    def test_only_one_default(self):
        addr1 = Address.objects.create(
            user=self.user, label='home', full_name='Test', phone='555-0100',
            street_address='1 A St', city='NY', state='NY',
            zip_code='10001', country='US', is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user, label='work', full_name='Test', phone='555-0100',
            street_address='2 B St', city='NY', state='NY',
            zip_code='10001', country='US', is_default=True
        )
        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_newsletter_subscriber(self):
        sub = NewsletterSubscriber.objects.create(email='news@test.com')
        self.assertTrue(sub.is_active)
        self.assertEqual(str(sub), 'news@test.com')


# ─── Menu Models ─────────────────────────────────────────────────────────────

class CategoryModelTest(TestCase):
    def test_create_category(self):
        cat = make_category()
        self.assertEqual(str(cat), 'Burgers')
        self.assertTrue(cat.is_active)

    def test_slug_auto_generated(self):
        cat = Category(name='Fresh Salads')
        cat.save()
        self.assertEqual(cat.slug, 'fresh-salads')

    def test_item_count_property(self):
        cat = make_category()
        make_item(category=cat, name='Burger 1')
        make_item(category=cat, name='Burger 2', is_available=False)
        self.assertEqual(cat.item_count, 1)


class MenuItemModelTest(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_str(self):
        self.assertEqual(str(self.item), 'Classic Burger')

    def test_discount_percent(self):
        self.item.old_price = Decimal('15.99')
        self.item.price = Decimal('12.99')
        self.item.save()
        self.assertGreater(self.item.discount_percent, 0)

    def test_no_discount_without_old_price(self):
        self.assertEqual(self.item.discount_percent, 0)

    def test_average_rating_no_reviews(self):
        self.assertEqual(self.item.average_rating, 0.0)

    def test_slug_auto_generated(self):
        self.assertEqual(self.item.slug, 'classic-burger')

    def test_get_image_url_fallback(self):
        url = self.item.get_image_url()
        self.assertIn('/static/', url)

    def test_short_description_auto(self):
        item = MenuItem(
            name='Test Item', category=self.cat,
            price=Decimal('10.00'), description='A' * 200
        )
        item.save()
        self.assertLessEqual(len(item.short_description), 150)


# ─── Cart Logic ──────────────────────────────────────────────────────────────

class CartTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = make_category()
        self.item1 = make_item(name='Burger', price='12.99', category=self.cat)
        self.item2 = make_item(name='Pizza', price='14.99', category=self.cat)

    def _get_cart(self):
        session = self.client.session
        response = self.client.get(reverse('cart'))
        return Cart(response.wsgi_request)

    def test_add_to_cart(self):
        response = self.client.post(
            reverse('cart_add', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 2})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['cart_count'], 2)

    def test_remove_from_cart(self):
        self.client.post(
            reverse('cart_add', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 1})
        )
        response = self.client.post(
            reverse('cart_remove', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['cart_count'], 0)

    def test_update_cart_quantity(self):
        self.client.post(
            reverse('cart_add', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 1})
        )
        response = self.client.post(
            reverse('cart_update', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 3})
        )
        data = response.json()
        self.assertEqual(data['cart_count'], 3)

    def test_cart_summary_endpoint(self):
        self.client.post(
            reverse('cart_add', args=[self.item1.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 1})
        )
        response = self.client.get(reverse('cart_summary'))
        data = response.json()
        self.assertIn('total', data)
        self.assertIn('count', data)

    def test_cart_detail_view(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cart')

    def test_cart_subtotal_calculation(self):
        session = self.client.session
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.item1, quantity=2)
        cart.add(self.item2, quantity=1)
        expected = Decimal('12.99') * 2 + Decimal('14.99')
        self.assertEqual(cart.get_subtotal(), expected)

    def test_free_delivery_threshold(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.session = self.client.session
        cart = Cart(request)
        expensive_item = make_item(name='Expensive', price='50.00', category=self.cat)
        cart.add(expensive_item, quantity=1)
        self.assertEqual(cart.get_delivery_fee(), Decimal('0.00'))

    def test_delivery_fee_below_threshold(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.item1, quantity=1)
        self.assertGreater(cart.get_delivery_fee(), Decimal('0.00'))


# ─── Order Models ─────────────────────────────────────────────────────────────

class OrderModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_order_number_auto_generated(self):
        order = make_order(user=self.user)
        self.assertTrue(order.order_number.startswith('SR'))
        self.assertEqual(len(order.order_number), 10)

    def test_order_str(self):
        order = make_order()
        self.assertIn('SR', str(order))

    def test_can_cancel_pending(self):
        order = make_order(status=Order.STATUS_PENDING)
        self.assertTrue(order.can_cancel)

    def test_cannot_cancel_delivered(self):
        order = make_order(status=Order.STATUS_DELIVERED)
        self.assertFalse(order.can_cancel)

    def test_status_display_class(self):
        order = make_order(status=Order.STATUS_DELIVERED)
        self.assertEqual(order.get_status_display_class(), 'success')
        order.status = Order.STATUS_CANCELLED
        self.assertEqual(order.get_status_display_class(), 'danger')

    def test_order_item_subtotal(self):
        order = make_order()
        cat = make_category()
        item = make_item(category=cat)
        oi = OrderItem.objects.create(
            order=order, menu_item=item,
            name=item.name, price=Decimal('12.99'), quantity=3
        )
        self.assertEqual(oi.subtotal, Decimal('38.97'))

    def test_order_status_update(self):
        order = make_order()
        upd = OrderStatusUpdate.objects.create(
            order=order, status=Order.STATUS_CONFIRMED, note='Test note'
        )
        self.assertEqual(str(upd), f'{order.order_number} -> {Order.STATUS_CONFIRMED}')

    def test_coupon_percent_discount(self):
        coupon = Coupon.objects.create(
            code='TEST20', discount_type='percent', discount_value=Decimal('20'),
            valid_from=timezone.now(), valid_until=timezone.now() + timedelta(days=30),
            is_active=True
        )
        discount = coupon.calculate_discount(Decimal('50.00'))
        self.assertEqual(discount, Decimal('10.00'))

    def test_coupon_fixed_discount(self):
        coupon = Coupon.objects.create(
            code='FIXED5', discount_type='fixed', discount_value=Decimal('5'),
            valid_from=timezone.now(), valid_until=timezone.now() + timedelta(days=30),
            is_active=True
        )
        discount = coupon.calculate_discount(Decimal('50.00'))
        self.assertEqual(discount, Decimal('5.00'))


# ─── Reservation Models ───────────────────────────────────────────────────────

class ReservationModelTest(TestCase):
    def test_confirmation_code_auto_generated(self):
        res = Reservation.objects.create(
            full_name='Jane Doe', email='jane@test.com', phone='555-0200',
            date=date.today() + timedelta(days=3), time='19:00', guests=2
        )
        self.assertTrue(res.confirmation_code.startswith('RES'))
        self.assertEqual(len(res.confirmation_code), 9)

    def test_reservation_str(self):
        res = Reservation.objects.create(
            full_name='Jane Doe', email='jane@test.com', phone='555-0200',
            date=date.today() + timedelta(days=3), time='19:00', guests=2
        )
        self.assertIn('Jane Doe', str(res))

    def test_table_str(self):
        t = Table.objects.create(number=1, capacity=4, location='indoor')
        self.assertIn('Table 1', str(t))


# ─── Review & Wishlist ────────────────────────────────────────────────────────

class ReviewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_create_review(self):
        review = Review.objects.create(
            menu_item=self.item, user=self.user,
            rating=5, comment='Amazing!'
        )
        self.assertEqual(str(review), f'{self.user.email} - {self.item} (5★)')

    def test_average_rating_with_reviews(self):
        u2 = make_user(email='u2@test.com')
        Review.objects.create(menu_item=self.item, user=self.user, rating=5, comment='Great')
        Review.objects.create(menu_item=self.item, user=u2, rating=3, comment='OK')
        self.assertEqual(self.item.average_rating, 4.0)

    def test_wishlist_creation(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
        wishlist.items.add(self.item)
        self.assertIn(self.item, wishlist.items.all())

    def test_wishlist_remove(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
        wishlist.items.add(self.item)
        wishlist.items.remove(self.item)
        self.assertNotIn(self.item, wishlist.items.all())


# ─── Views ───────────────────────────────────────────────────────────────────

class HomeViewTest(TestCase):
    def test_home_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'menu/home.html')
        self.assertTemplateUsed(response, 'base/base.html')

    def test_home_has_categories_context(self):
        make_category()
        response = self.client.get(reverse('home'))
        self.assertIn('categories', response.context)

    def test_home_has_menu_items_context(self):
        response = self.client.get(reverse('home'))
        self.assertIn('menu_items', response.context)


class MenuViewTest(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_full_menu_200(self):
        response = self.client.get(reverse('full_menu'))
        self.assertEqual(response.status_code, 200)

    def test_full_menu_filter_by_category(self):
        response = self.client.get(reverse('full_menu') + '?category=burgers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_category'], 'burgers')

    def test_full_menu_search(self):
        response = self.client.get(reverse('full_menu') + '?q=Burger')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Classic Burger')

    def test_menu_item_detail_200(self):
        response = self.client.get(reverse('menu_item_detail', args=[self.item.slug]))
        self.assertEqual(response.status_code, 200)

    def test_menu_item_detail_404(self):
        response = self.client.get(reverse('menu_item_detail', args=['nonexistent-item']))
        self.assertEqual(response.status_code, 404)

    def test_menu_search_ajax(self):
        response = self.client.get(reverse('menu_search') + '?q=Burger')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)

    def test_menu_search_short_query_returns_empty(self):
        response = self.client.get(reverse('menu_search') + '?q=B')
        data = response.json()
        self.assertIsInstance(data["results"], list)


class AccountViewTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_register_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_post_valid(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'New', 'last_name': 'User',
            'email': 'newuser@test.com',
            'password1': 'SecurePass123!', 'password2': 'SecurePass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='newuser@test.com').exists())

    def test_register_redirect_if_logged_in(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('home'))

    def test_login_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_post_valid(self):
        response = self.client.post(reverse('login'), {
            'username': 'test@sarab.com', 'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_post_invalid(self):
        response = self.client.post(reverse('login'), {
            'username': 'test@sarab.com', 'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, '/accounts/login/?next=/accounts/profile/')

    def test_profile_authenticated(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')

    def test_add_address(self):
        """Regression test: the add-address form previously had no way to
        submit `country`, a required AddressForm field, so every
        submission silently failed validation and nothing was ever
        saved."""
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.post(reverse('add_address'), {
            'label': 'home', 'full_name': 'Test User', 'phone': '555-0100',
            'street_address': '123 Test St', 'city': 'New York', 'state': 'NY',
            'zip_code': '10001', 'country': 'United States',
        })
        self.assertRedirects(response, reverse('addresses'))
        self.assertTrue(Address.objects.filter(user=self.user, full_name='Test User').exists())

    def test_add_address_sets_default_exclusively(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        first = Address.objects.create(
            user=self.user, full_name='First', phone='555', street_address='1 St',
            city='NY', state='NY', zip_code='10001', country='United States', is_default=True,
        )
        self.client.post(reverse('add_address'), {
            'label': 'work', 'full_name': 'Second', 'phone': '555-0200',
            'street_address': '456 Ave', 'city': 'New York', 'state': 'NY',
            'zip_code': '10002', 'country': 'United States', 'is_default': 'on',
        })
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(Address.objects.get(full_name='Second').is_default)

    def test_edit_address(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        address = Address.objects.create(
            user=self.user, full_name='Old Name', phone='555', street_address='1 St',
            city='NY', state='NY', zip_code='10001', country='United States',
        )
        response = self.client.post(reverse('edit_address', args=[address.pk]), {
            'label': 'work', 'full_name': 'New Name', 'phone': '555-0300',
            'street_address': '789 Blvd', 'city': 'Boston', 'state': 'MA',
            'zip_code': '02101', 'country': 'United States',
        })
        self.assertRedirects(response, reverse('addresses'))
        address.refresh_from_db()
        self.assertEqual(address.full_name, 'New Name')
        self.assertEqual(address.city, 'Boston')

    def test_edit_address_blocks_other_users(self):
        other = make_user(email='other4@sarab.com')
        address = Address.objects.create(
            user=other, full_name='Other User', phone='555', street_address='1 St',
            city='NY', state='NY', zip_code='10001', country='United States',
        )
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('edit_address', args=[address.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_address(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        address = Address.objects.create(
            user=self.user, full_name='To Delete', phone='555', street_address='1 St',
            city='NY', state='NY', zip_code='10001', country='United States',
        )
        response = self.client.post(reverse('delete_address', args=[address.pk]))
        self.assertRedirects(response, reverse('addresses'))
        self.assertFalse(Address.objects.filter(pk=address.pk).exists())


class OrderViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_checkout_redirects_empty_cart(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, reverse('full_menu'))

    def test_checkout_with_items(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        self.client.post(
            reverse('cart_add', args=[self.item.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 1})
        )
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)

    def test_order_history_requires_login(self):
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 302)

    def test_order_history_authenticated(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)

    def test_order_success_page(self):
        order = make_order(user=self.user)
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('order_success', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)

    def test_order_tracking_page(self):
        order = make_order(user=self.user)
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('order_tracking', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_order_success_page_blocks_other_users(self):
        """Regression test: another logged-in user must not be able to
        view this order just by knowing its order_number (IDOR)."""
        order = make_order(user=self.user)
        other = make_user(email='other@sarab.com')
        self.client.login(username='other@sarab.com', password='testpass123')
        response = self.client.get(reverse('order_success', args=[order.order_number]))
        self.assertEqual(response.status_code, 403)

    def test_order_success_page_allows_guest_who_just_ordered(self):
        """A guest checkout should still be able to see their own
        confirmation page right after placing the order (tracked via
        session['last_order_id']), without needing an account."""
        order = make_order(user=None)
        session = self.client.session
        session['last_order_id'] = order.id
        session.save()
        response = self.client.get(reverse('order_success', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_apply_coupon_valid(self):
        Coupon.objects.create(
            code='TEST10', discount_type='percent', discount_value=10,
            valid_from=timezone.now(), valid_until=timezone.now() + timedelta(days=30),
            is_active=True
        )
        self.client.post(
            reverse('cart_add', args=[self.item.id]),
            content_type='application/json', data=json.dumps({'quantity': 1})
        )
        response = self.client.post(
            reverse('apply_coupon'),
            content_type='application/json',
            data=json.dumps({'code': 'TEST10'})
        )
        data = response.json()
        self.assertEqual(data['status'], 'ok')

    def test_apply_coupon_invalid(self):
        response = self.client.post(
            reverse('apply_coupon'),
            content_type='application/json',
            data=json.dumps({'code': 'BADCODE'})
        )
        data = response.json()
        self.assertEqual(data['status'], 'error')


class ReservationViewTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_reservation_form_get(self):
        response = self.client.get(reverse('make_reservation'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reservations/make_reservation.html')

    def test_reservation_post_json(self):
        future_date = (date.today() + timedelta(days=3)).isoformat()
        response = self.client.post(
            reverse('make_reservation'),
            content_type='application/json',
            data=json.dumps({
                'full_name': 'Jane Doe', 'email': 'jane@test.com',
                'phone': '555-0200', 'guests': 2,
                'date': future_date, 'time': '19:00',
                'csrfmiddlewaretoken': 'dummy'
            }),
            HTTP_X_CSRFTOKEN='dummy'
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                self.assertTrue(Reservation.objects.filter(email='jane@test.com').exists())

    def test_reservation_history_requires_login(self):
        response = self.client.get(reverse('reservation_history'))
        self.assertEqual(response.status_code, 302)

    def test_reservation_history_authenticated(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('reservation_history'))
        self.assertEqual(response.status_code, 200)

    def test_reservation_confirmation_page(self):
        res = Reservation.objects.create(
            full_name='Test', email='t@t.com', phone='555',
            date=date.today() + timedelta(days=1), time='19:00', guests=2
        )
        response = self.client.get(reverse('reservation_confirmation', args=[res.confirmation_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, res.confirmation_code)

    def test_reservation_confirmation_page_blocks_other_users(self):
        """Regression test: a reservation attached to an account must not
        be viewable by a different account via the confirmation code
        (guest reservations with no account are unaffected)."""
        res = Reservation.objects.create(
            user=self.user, full_name='Test', email='t@t.com', phone='555',
            date=date.today() + timedelta(days=1), time='19:00', guests=2
        )
        make_user(email='other3@sarab.com')
        self.client.login(username='other3@sarab.com', password='testpass123')
        response = self.client.get(reverse('reservation_confirmation', args=[res.confirmation_code]))
        self.assertEqual(response.status_code, 403)


class CMSViewTest(TestCase):
    def test_about_200(self):
        self.assertEqual(self.client.get(reverse('about')).status_code, 200)

    def test_contact_200(self):
        self.assertEqual(self.client.get(reverse('contact')).status_code, 200)

    def test_faq_200(self):
        self.assertEqual(self.client.get(reverse('faq')).status_code, 200)

    def test_privacy_200(self):
        self.assertEqual(self.client.get(reverse('privacy_policy')).status_code, 200)

    def test_terms_200(self):
        self.assertEqual(self.client.get(reverse('terms')).status_code, 200)

    def test_refund_200(self):
        self.assertEqual(self.client.get(reverse('refund_policy')).status_code, 200)

    def test_blog_list_200(self):
        self.assertEqual(self.client.get(reverse('blog_list')).status_code, 200)

    def test_contact_submit_ajax(self):
        response = self.client.post(
            reverse('contact_submit'),
            content_type='application/json',
            data=json.dumps({
                'name': 'Test Person', 'email': 'tp@test.com',
                'subject': 'Test', 'message': 'Hello world'
            })
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(ContactMessage.objects.filter(email='tp@test.com').exists())

    def test_newsletter_subscribe_new(self):
        response = self.client.post(
            reverse('newsletter_subscribe'),
            content_type='application/json',
            data=json.dumps({'email': 'subscriber@test.com'})
        )
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(NewsletterSubscriber.objects.filter(email='subscriber@test.com').exists())

    def test_newsletter_subscribe_duplicate(self):
        NewsletterSubscriber.objects.create(email='already@test.com')
        response = self.client.post(
            reverse('newsletter_subscribe'),
            content_type='application/json',
            data=json.dumps({'email': 'already@test.com'})
        )
        data = response.json()
        self.assertEqual(data['status'], 'exists')

    def test_newsletter_invalid_email(self):
        response = self.client.post(
            reverse('newsletter_subscribe'),
            content_type='application/json',
            data=json.dumps({'email': 'notanemail'})
        )
        self.assertEqual(response.status_code, 400)


class WishlistViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_wishlist_requires_login(self):
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 302)

    def test_wishlist_authenticated(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)

    def test_toggle_wishlist_add(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.post(
            reverse('toggle_wishlist', args=[self.item.id]),
            content_type='application/json'
        )
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['added'])

    def test_toggle_wishlist_remove(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
        wishlist.items.add(self.item)
        response = self.client.post(
            reverse('toggle_wishlist', args=[self.item.id]),
            content_type='application/json'
        )
        data = response.json()
        self.assertFalse(data['added'])


class PaymentViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.login(username='test@sarab.com', password='testpass123')

    def test_payment_success_page(self):
        order = make_order(user=self.user)
        response = self.client.get(reverse('payment_success', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Successful')

    def test_payment_failed_page(self):
        order = make_order(user=self.user)
        response = self.client.get(reverse('payment_failed', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_invoice_page(self):
        order = make_order(user=self.user)
        response = self.client.get(reverse('invoice', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)
        self.assertContains(response, 'INVOICE')

    def test_invoice_page_blocks_other_users(self):
        """Regression test: an unrelated logged-in user must not be able
        to view someone else's invoice by guessing/knowing the order
        number (IDOR)."""
        order = make_order(user=self.user)
        make_user(email='other2@sarab.com')
        self.client.logout()
        self.client.login(username='other2@sarab.com', password='testpass123')
        response = self.client.get(reverse('invoice', args=[order.order_number]))
        self.assertEqual(response.status_code, 403)


# ─── API Tests ───────────────────────────────────────────────────────────────

class APITest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.cat = make_category()
        self.item = make_item(category=self.cat)

    def test_categories_api(self):
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)

    def test_menu_api(self):
        response = self.client.get('/api/v1/menu/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertGreater(data['count'], 0)

    def test_menu_api_search(self):
        response = self.client.get('/api/v1/menu/?search=Burger')
        self.assertEqual(response.status_code, 200)

    def test_menu_api_filter_by_category(self):
        response = self.client.get('/api/v1/menu/?category=burgers')
        self.assertEqual(response.status_code, 200)

    def test_orders_api_requires_auth(self):
        response = self.client.get('/api/v1/orders/')
        self.assertIn(response.status_code, [401, 403])

    def test_orders_api_authenticated(self):
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get('/api/v1/orders/')
        self.assertEqual(response.status_code, 200)

    def test_reservations_api_get(self):
        response = self.client.get('/api/v1/reservations/')
        self.assertEqual(response.status_code, 200)

    def test_reviews_api_get(self):
        response = self.client.get('/api/v1/reviews/')
        self.assertEqual(response.status_code, 200)

    def test_menu_item_detail_api(self):
        response = self.client.get(f'/api/v1/menu/{self.item.slug}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], self.item.name)
        self.assertIn('average_rating', data)
        self.assertIn('review_count', data)

    def test_category_detail_api(self):
        response = self.client.get(f'/api/v1/categories/{self.cat.slug}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], self.cat.name)


# ─── CMS Model Tests ─────────────────────────────────────────────────────────

class CMSModelTest(TestCase):
    def test_faq_str(self):
        faq = FAQ.objects.create(
            question='Is delivery free?', answer='Yes over $30.', order=1
        )
        self.assertEqual(str(faq), 'Is delivery free?')

    def test_blog_post_str(self):
        post = BlogPost.objects.create(
            title='Test Post', slug='test-post', author='Chef',
            excerpt='Short excerpt.', content='Full content here.',
        )
        self.assertEqual(str(post), 'Test Post')


# ─── Context Processors ───────────────────────────────────────────────────────

class AdminSiteAccessTest(TestCase):
    """Regression tests for config/admin_dashboard.py's has_permission override —
    Django Admin access previously only checked is_staff, ignoring this
    project's own customer/staff/admin role distinction entirely."""

    def test_admin_role_can_access_dashboard(self):
        user = CustomUser.objects.create_superuser(
            email='dashadmin@sarab.com', username='dashadmin@sarab.com',
            password='pass123', role=CustomUser.ROLE_ADMIN,
        )
        self.client.login(username='dashadmin@sarab.com', password='pass123')
        response = self.client.get(reverse('admin:index'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Site administration')

    def test_staff_role_blocked_from_dashboard(self):
        """A role=staff account, even with is_staff=True, must not reach
        any admin page — only role=admin (or a superuser) may."""
        user = CustomUser.objects.create_user(
            email='juststaff@sarab.com', username='juststaff@sarab.com',
            password='pass123', role=CustomUser.ROLE_STAFF, is_staff=True,
        )
        self.client.login(username='juststaff@sarab.com', password='pass123')
        response = self.client.get(reverse('admin:index'), follow=True)
        self.assertNotContains(response, 'Site administration')

    def test_customer_blocked_from_dashboard(self):
        make_user()
        self.client.login(username='test@sarab.com', password='testpass123')
        response = self.client.get(reverse('admin:index'), follow=True)
        self.assertNotContains(response, 'Site administration')

    def test_dashboard_shows_stats(self):
        """Regression coverage for the custom admin index (config/admin_dashboard.py
        ::_dashboard_index / templates/admin/index.html) — previously the
        dashboard was just Django's bare app/model list with no overview."""
        admin_user = CustomUser.objects.create_superuser(
            email='statsadmin@sarab.com', username='statsadmin@sarab.com',
            password='pass123', role=CustomUser.ROLE_ADMIN,
        )
        make_order(user=admin_user)  # gives "Today's Orders"/"Recent Orders" something to show
        self.client.login(username='statsadmin@sarab.com', password='pass123')
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's Orders")
        self.assertContains(response, 'Pending Orders')
        self.assertContains(response, 'Pending Reservations')
        self.assertContains(response, 'Unread Messages')

    def test_bulk_mark_order_confirmed_creates_status_update(self):
        """The bulk order-status admin actions must go through save() +
        OrderStatusUpdate.objects.create() like the customer-facing
        cancel_order view does — not a bare queryset.update(), which
        would silently skip the tracking record order_tracking depends
        on."""
        admin_user = CustomUser.objects.create_superuser(
            email='bulkadmin@sarab.com', username='bulkadmin@sarab.com',
            password='pass123', role=CustomUser.ROLE_ADMIN,
        )
        order = make_order(user=admin_user)
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.client.login(username='bulkadmin@sarab.com', password='pass123')
        self.client.post('/admin/orders/order/', {
            'action': 'mark_confirmed',
            '_selected_action': [str(order.pk)],
        })
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertTrue(order.status_updates.filter(status=Order.STATUS_CONFIRMED).exists())

    def test_bulk_mark_reservation_confirmed(self):
        admin_user = CustomUser.objects.create_superuser(
            email='resbulkadmin@sarab.com', username='resbulkadmin@sarab.com',
            password='pass123', role=CustomUser.ROLE_ADMIN,
        )
        reservation = Reservation.objects.create(
            full_name='Test', email='t@t.com', phone='555',
            date=date.today() + timedelta(days=1), time='19:00', guests=2,
        )
        self.assertEqual(reservation.status, Reservation.STATUS_PENDING)
        self.client.login(username='resbulkadmin@sarab.com', password='pass123')
        self.client.post('/admin/reservations/reservation/', {
            'action': 'mark_confirmed',
            '_selected_action': [str(reservation.pk)],
        })
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.STATUS_CONFIRMED)


class ContextProcessorTest(TestCase):
    def setUp(self):
        make_category(name='Test Cat', slug='test-cat')

    def test_all_categories_in_context(self):
        response = self.client.get(reverse('home'))
        self.assertIn('all_categories', response.context)
        cats = list(response.context['all_categories'])
        slugs = [c.slug for c in cats]
        self.assertIn('test-cat', slugs)

    def test_cart_count_in_context(self):
        response = self.client.get(reverse('home'))
        self.assertIn('cart_count', response.context)
        self.assertEqual(response.context['cart_count'], 0)

    def test_cart_count_after_add(self):
        cat = make_category()
        item = make_item(category=cat)
        self.client.post(
            reverse('cart_add', args=[item.id]),
            content_type='application/json',
            data=json.dumps({'quantity': 2})
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['cart_count'], 2)
