from django.db import models
from django.utils.text import slugify
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default='fas fa-utensils')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # There's no dedicated per-category page/route — categories are
        # browsed via the full menu filtered by ?category=<slug>
        # (see menu/views.py:full_menu). This previously pointed at a
        # 'menu_category' URL name that was never defined anywhere,
        # which would 500 the moment anything called it — including
        # Django Admin's automatic "View on site" link for this model.
        return f"{reverse('full_menu')}?category={self.slug}"

    @property
    def item_count(self):
        # Use the annotated value when the queryset supplied one
        # (see menu/views.py / api/views.py) to avoid one query per
        # category when rendering a list; falls back to a live query
        # for a single object fetched on its own.
        if hasattr(self, '_item_count'):
            return self._item_count
        return self.items.filter(is_available=True).count()


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(models.Model):
    BADGE_NONE = ''
    BADGE_HOT = 'hot'
    BADGE_NEW = 'new'
    BADGE_BESTSELLER = 'bestseller'
    BADGE_CHEFS_PICK = 'chefs_pick'
    BADGE_CHOICES = [
        (BADGE_NONE, 'None'),
        (BADGE_HOT, 'Hot'),
        (BADGE_NEW, 'New'),
        (BADGE_BESTSELLER, 'Best Seller'),
        (BADGE_CHEFS_PICK, "Chef's Pick"),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='menu/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, default=BADGE_NONE, blank=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    prep_time = models.PositiveIntegerField(null=True, blank=True, help_text='Minutes')
    is_available = models.BooleanField(default=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.short_description:
            self.short_description = self.description[:150]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('menu_item_detail', kwargs={'slug': self.slug})

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0

    @property
    def average_rating(self):
        # Same annotation-first pattern as Category.item_count above.
        if hasattr(self, '_avg_rating'):
            return round(self._avg_rating, 1) if self._avg_rating else 0.0
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0.0

    @property
    def review_count(self):
        if hasattr(self, '_review_count'):
            return self._review_count
        return self.reviews.count()

    def get_image_url(self):
        if self.image:
            return self.image.url
        # fallback to static image by category
        mapping = {
            'burgers': 'img/menu/1.jpg',
            'pizza': 'img/menu/2.jpg',
            'chicken': 'img/menu/3.jpg',
            'wraps': 'img/menu/4.jpg',
            'desserts': 'img/menu/5.jpg',
            'pasta': 'img/menu/6.jpg',
        }
        return '/static/' + mapping.get(self.category.slug, 'img/menu/1.jpg')


class MenuItemVariation(models.Model):
    """Size/variation options like Small/Medium/Large"""
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.item.name} - {self.name}"


class MenuItemAddon(models.Model):
    """Extra add-ons like extra cheese, sauce etc."""
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.item.name} + {self.name}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
