from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_avatar_size(file):
    # Customer-facing upload, unlike menu/category images which are
    # only ever set by staff through Django admin — cap it so a user
    # can't fill disk with oversized uploads (no limit existed before).
    max_bytes = 5 * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError('Image file too large ( max 5MB ).')


class CustomUser(AbstractUser):
    ROLE_CUSTOMER = 'customer'
    ROLE_STAFF = 'staff'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_ADMIN, 'Admin'),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, validators=[validate_avatar_size])
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    email_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_staff_user(self):
        return self.role in [self.ROLE_STAFF, self.ROLE_ADMIN] or self.is_staff


class Address(models.Model):
    TYPE_HOME = 'home'
    TYPE_WORK = 'work'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_HOME, 'Home'),
        (TYPE_WORK, 'Work'),
        (TYPE_OTHER, 'Other'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_HOME)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        # Enforced here (not just in the views) so every path that can
        # create/update an address — admin, API, future code — gets
        # the same "only one default per user" guarantee, matching
        # what tests.py's test_only_one_default already expects of
        # Address.objects.create() directly.
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.label} - {self.street_address}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email
