"""
Management command: python manage.py seed_data
Seeds the database with realistic sample data for all apps.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding Sarab database...'))
        self._seed_categories()
        self._seed_tags()
        self._seed_menu_items()
        self._seed_users()
        self._seed_coupons()
        self._seed_tables()
        self._seed_faqs()
        self._seed_blog_posts()
        self._seed_reservations()
        self._seed_reviews()
        self.stdout.write(self.style.SUCCESS('✓ Seed complete!'))

    def _seed_categories(self):
        from menu.models import Category
        cats = [
            ('Burgers', 'burgers', 'fas fa-hamburger', 1),
            ('Pizza', 'pizza', 'fas fa-pizza-slice', 2),
            ('Fried Chicken', 'chicken', 'fas fa-drumstick-bite', 3),
            ('Wraps', 'wraps', 'fas fa-bread-slice', 4),
            ('Pasta', 'pasta', 'fas fa-utensils', 5),
            ('Desserts', 'desserts', 'fas fa-ice-cream', 6),
            ('Drinks', 'drinks', 'fas fa-glass-water', 7),
            ('Sides', 'sides', 'fas fa-bowl-food', 8),
        ]
        for name, slug, icon, order in cats:
            Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'order': order, 'is_active': True}
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(cats)} categories'))

    def _seed_tags(self):
        from menu.models import Tag
        tags = ['Bestseller', 'Spicy', 'Vegan', 'Gluten-Free', 'Signature', 'Chef Special', 'Seasonal']
        for tag in tags:
            from django.utils.text import slugify
            Tag.objects.get_or_create(name=tag, defaults={'slug': slugify(tag)})
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(tags)} tags'))

    def _seed_menu_items(self):
        from menu.models import Category, MenuItem
        from django.utils.text import slugify
        items = [
            ('Classic Smash Burger', 'burgers', '12.99', '15.99', 'hot', True),
            ('BBQ Bacon Burger', 'burgers', '14.99', None, 'bestseller', True),
            ('Veggie Delight Burger', 'burgers', '11.99', '13.99', 'new', False),
            ('Truffle Mushroom Burger', 'burgers', '15.99', None, '', True),
            ('Double Cheeseburger', 'burgers', '13.49', None, 'hot', True),
            ('Margherita Pizza', 'pizza', '13.99', None, '', False),
            ('Pepperoni BBQ Pizza', 'pizza', '15.99', '18.99', 'hot', False),
            ('Truffle White Pizza', 'pizza', '17.99', None, 'chefs_pick', False),
            ('Veggie Supreme Pizza', 'pizza', '14.99', None, 'new', True),
            ('Nashville Chicken Sandwich', 'chicken', '13.99', '15.99', 'hot', False),
            ('Southern Fried Box', 'chicken', '14.99', None, 'bestseller', False),
            ('Honey Glazed Tenders', 'chicken', '11.99', None, '', False),
            ('BBQ Chicken Wrap', 'wraps', '10.99', '12.99', '', False),
            ('Falafel Avocado Wrap', 'wraps', '9.99', None, 'new', True),
            ('Grilled Chicken Caesar Wrap', 'wraps', '11.49', None, '', False),
            ('Truffle Mac & Cheese', 'pasta', '11.99', None, '', False),
            ('Penne Arrabiata', 'pasta', '10.99', None, '', True),
            ('Creamy Chicken Alfredo', 'pasta', '13.49', None, 'bestseller', False),
            ('Molten Lava Cake', 'desserts', '7.99', '9.99', 'bestseller', False),
            ('Cheesecake Slice', 'desserts', '6.99', None, '', False),
            ('Cookie Dough Sundae', 'desserts', '8.49', None, 'new', False),
            ('Loaded Oreo Milkshake', 'drinks', '6.99', None, 'new', False),
            ('Fresh Lemonade', 'drinks', '4.49', None, '', False),
            ('Iced Caramel Latte', 'drinks', '5.49', None, '', False),
            ('Loaded Fries', 'sides', '7.99', '9.99', 'hot', False),
            ('Onion Rings', 'sides', '5.99', None, '', False),
            ('Coleslaw', 'sides', '3.49', None, '', False),
        ]
        count = 0
        for name, cat_slug, price, old_price, badge, featured in items:
            try:
                cat = Category.objects.get(slug=cat_slug)
                slug = slugify(name)
                if not MenuItem.objects.filter(slug=slug).exists():
                    MenuItem.objects.create(
                        name=name, slug=slug, category=cat,
                        price=Decimal(price),
                        old_price=Decimal(old_price) if old_price else None,
                        badge=badge, is_featured=featured,
                        description=f'Delicious {name} made fresh daily with premium ingredients.',
                        short_description=f'Premium {name} crafted with care.',
                        calories=random.randint(300, 900),
                        prep_time=random.randint(8, 22),
                        is_available=True,
                    )
                    count += 1
            except Category.DoesNotExist:
                pass
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} menu items'))

    def _seed_users(self):
        from accounts.models import CustomUser

        # Only account that should actually be able to log into Django
        # Admin, matching the "role must be admin" gate enforced in
        # config/admin_dashboard.py — everything else below is
        # role=customer/staff, which is deliberately NOT enough for
        # admin access on its own (is_staff alone isn't checked either).
        if not CustomUser.objects.filter(email='admin@sarab.com').exists():
            CustomUser.objects.create_superuser(
                email='admin@sarab.com', username='admin@sarab.com', password='admin123',
                first_name='Sarab', last_name='Admin', role=CustomUser.ROLE_ADMIN,
            )

        users = [
            ('customer@sarab.com', 'Alex', 'Johnson', CustomUser.ROLE_CUSTOMER),
            ('jane@sarab.com', 'Jane', 'Smith', CustomUser.ROLE_CUSTOMER),
            ('staff@sarab.com', 'Staff', 'Member', CustomUser.ROLE_STAFF),
        ]
        count = 0
        for email, fn, ln, role in users:
            if not CustomUser.objects.filter(email=email).exists():
                CustomUser.objects.create_user(
                    email=email, username=email, password='sarab2026',
                    first_name=fn, last_name=ln, role=role
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} sample users (password: sarab2026)'))
        self.stdout.write(self.style.SUCCESS('  ✓ 1 admin account (admin@sarab.com / admin123)'))

    def _seed_coupons(self):
        from orders.models import Coupon
        coupons = [
            ('WELCOME15', 'percent', 15, 0),
            ('SAVE5', 'fixed', 5, 20),
            ('FRIDAY20', 'percent', 20, 30),
        ]
        for code, dtype, value, min_amt in coupons:
            Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'discount_type': dtype,
                    'discount_value': Decimal(str(value)),
                    'min_order_amount': Decimal(str(min_amt)),
                    'valid_from': timezone.now(),
                    'valid_until': timezone.now() + timedelta(days=365),
                    'is_active': True,
                }
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(coupons)} coupons'))

    def _seed_tables(self):
        from reservations.models import Table
        tables = [
            (1, 2, 'indoor'), (2, 4, 'indoor'), (3, 4, 'indoor'),
            (4, 6, 'indoor'), (5, 2, 'indoor'), (6, 4, 'indoor'),
            (7, 4, 'outdoor'), (8, 6, 'outdoor'), (9, 8, 'outdoor'),
            (10, 4, 'vip'), (11, 6, 'vip'), (12, 2, 'bar'),
        ]
        for num, cap, loc in tables:
            Table.objects.get_or_create(number=num, defaults={'capacity': cap, 'location': loc})
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(tables)} tables'))

    def _seed_faqs(self):
        from cms_pages.models import FAQ
        faqs = [
            (1, 'What are your delivery hours?', 'We deliver Wednesday through Sunday from 10 AM to 10:30 PM.'),
            (2, 'How long does delivery take?', 'Most deliveries arrive within 20–30 minutes.'),
            (3, 'Do you offer vegan options?', 'Yes! Look for the leaf icon on our menu.'),
            (4, 'Can I modify my order after placing it?', 'Orders can be modified within 5 minutes by calling us.'),
            (5, 'What is your refund policy?', 'Full refunds within 5 minutes. Quality issues resolved within 30 min.'),
            (6, 'Do you cater for large groups?', 'Yes! Email events@sarabfood.com for groups of 20+.'),
            (7, 'Is the food halal?', 'Yes — all our meat is certified halal.'),
            (8, 'How do I track my order?', 'Use the order tracking page with your order number.'),
        ]
        for order, q, a in faqs:
            FAQ.objects.get_or_create(question=q, defaults={'answer': a, 'order': order})
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(faqs)} FAQs'))

    def _seed_blog_posts(self):
        from cms_pages.models import BlogPost
        from django.utils.text import slugify
        posts = [
            ('Healthy Fast Food: A Myth or Beautiful Reality', 'Food & Health', 'James Writer', 'The truth about fast food nutrition and how Sarab approaches healthy eating without sacrificing flavour.'),
            ('Is Fast Food Getting Healthier?', 'Food Science', 'Sarah Grain', 'We investigate the trends transforming the fast food industry and what it means for you.'),
            ('The Secret Behind Our Smash Burger', 'Behind the Scenes', 'Chef Marcus', 'Head Chef Marcus reveals the 6-step technique that makes our burgers award-winning.'),
            ('Farm to Table: How We Source Ingredients', 'Sustainability', 'Diana Lee', 'A look at our relationships with local farms and why fresh sourcing matters so much to us.'),
            ('5 Nutritionist-Approved Fast Food Swaps', 'Nutrition', 'Dr. Patel', 'Simple swaps that let you enjoy fast food while staying on track with your health goals.'),
            ('Innovative Chickpea Crackers Recipe', 'Recipes', 'Chef Alice', 'Try our popular chickpea snack recipe at home — packed with protein and delicious flavour.'),
        ]
        from datetime import date as dt
        count = 0
        for i, (title, cat, author, excerpt) in enumerate(posts):
            slug = slugify(title)
            if not BlogPost.objects.filter(slug=slug).exists():
                pub = dt.today() - timedelta(days=i*14)
                BlogPost.objects.create(
                    title=title, slug=slug, author=author, category=cat,
                    excerpt=excerpt, content=excerpt + ' ' + excerpt * 3,
                    is_published=True, published_at=pub, comment_count=random.randint(5, 40)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} blog posts'))

    def _seed_reservations(self):
        from reservations.models import Reservation
        data = [
            ('Alice Wang', 'alice@example.com', '555-0101', 2, 'birthday'),
            ('Bob Martin', 'bob@example.com', '555-0102', 4, 'anniversary'),
            ('Carol Jones', 'carol@example.com', '555-0103', 6, 'business'),
        ]
        count = 0
        for name, email, phone, guests, occasion in data:
            if not Reservation.objects.filter(email=email).exists():
                Reservation.objects.create(
                    full_name=name, email=email, phone=phone,
                    date=date.today() + timedelta(days=random.randint(1, 14)),
                    time='19:00', guests=guests, occasion=occasion,
                    status=Reservation.STATUS_CONFIRMED
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} reservations'))

    def _seed_reviews(self):
        from reviews.models import Review
        from accounts.models import CustomUser
        from menu.models import MenuItem
        comments = [
            (5, 'Absolutely incredible! Best burger I\'ve ever had. The smash technique gives it that perfect crispy edge.'),
            (5, 'Food arrived hot and fresh in 22 minutes. Generous portions. Definitely ordering again!'),
            (4, 'Really good food. The Nashville chicken sandwich is 🔥. Slightly spicier than expected but loved it.'),
            (5, 'The truffle pasta blew my mind. Didn\'t expect that quality from a fast food place. Highly recommended!'),
            (4, 'Great value for money. Onion rings were perfectly crispy. Will be back for sure.'),
        ]
        users = list(CustomUser.objects.filter(role=CustomUser.ROLE_CUSTOMER)[:5])
        items = list(MenuItem.objects.filter(is_available=True)[:5])
        count = 0
        for i, ((rating, comment), user, item) in enumerate(zip(comments, users, items)):
            if not Review.objects.filter(menu_item=item, user=user).exists():
                Review.objects.create(
                    menu_item=item, user=user, rating=rating,
                    comment=comment, is_approved=True
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} reviews'))
