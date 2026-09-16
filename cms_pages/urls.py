from django.urls import path
from . import views

urlpatterns = [
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_conditions, name='terms'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path("support/", views.support_page, name="support_page"),
    path("support/chat/", views.support_chat_api, name="support_chat_api"),
]
