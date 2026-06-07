from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from .models import CustomUser, Address, NewsletterSubscriber
from .forms import RegisterForm, LoginForm, ProfileForm, AddressForm, CustomPasswordResetForm, CustomSetPasswordForm
import json


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'home')
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=request.user)
    orders = request.user.order_set.all()[:5] if hasattr(request.user, 'order_set') else []
    return render(request, 'accounts/profile.html', {'form': form, 'orders': orders})


@login_required
def addresses_view(request):
    addresses = request.user.addresses.all()
    form = AddressForm()
    return render(request, 'accounts/addresses.html', {'addresses': addresses, 'form': form})


@login_required
def add_address_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully.')
        else:
            messages.error(request, 'Please fill all required fields.')
    return redirect('addresses')


@login_required
def edit_address_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully.')
            return redirect('addresses')
    else:
        form = AddressForm(instance=address)
    return render(request, 'accounts/edit_address.html', {'form': form, 'address': address})


@login_required
def delete_address_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted.')
    return redirect('addresses')


@require_POST
def newsletter_subscribe(request):
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    email = data.get('email', '').strip()
    if email and '@' in email:
        obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if created:
            return JsonResponse({'status': 'ok', 'message': 'Subscribed! Check your email for a 15% discount.'})
        return JsonResponse({'status': 'exists', 'message': "You're already subscribed!"})
    return JsonResponse({'status': 'error', 'message': 'Please enter a valid email.'}, status=400)


class SarabPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = '/accounts/password-reset/done/'


class SarabPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = '/accounts/login/'
