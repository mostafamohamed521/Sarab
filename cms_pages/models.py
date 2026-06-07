from django.db import models


class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ'

    def __str__(self):
        return self.question


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.CharField(max_length=100)
    category = models.CharField(max_length=100, default='Food & Health')
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    excerpt = models.TextField(max_length=300)
    content = models.TextField()
    comment_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    published_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
