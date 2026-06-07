from django.db import models
from django.conf import settings


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['menu_item', 'user']

    def __str__(self):
        return f"{self.user.email} - {self.menu_item} ({self.rating}★)"


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    items = models.ManyToManyField('menu.MenuItem', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}'s Wishlist"
