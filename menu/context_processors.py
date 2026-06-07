from .models import Category

def categories_processor(request):
    return {'all_categories': Category.objects.filter(is_active=True)}
