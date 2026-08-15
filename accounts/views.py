from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from .models import Address, NewsletterSubscriber
from .forms import RegisterForm, LoginForm, ProfileForm, AddressForm, CustomPasswordResetForm, CustomSetPasswordForm
from config.ratelimit import is_rate_limited, record_attempt
import json


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        if is_rate_limited(request, 'register', max_attempts=10, window_seconds=3600):
            messages.error(request, 'Too many signup attempts. Please try again later.')
            return render(request, 'accounts/register.html', {'form': RegisterForm()})
        record_attempt(request, 'register', window_seconds=3600)
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
        # 10 attempts / 5 minutes per IP — generous enough not to lock
        # out someone who mistypes their password a couple of times,
        # tight enough to blunt a brute-force script. No such limit
        # existed before.
        if is_rate_limited(request, 'login', max_attempts=10, window_seconds=300):
            messages.error(request, 'Too many login attempts. Please wait a few minutes and try again.')
            return render(request, 'accounts/login.html', {'form': LoginForm()})
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # The "Remember me" checkbox existed in the template but
            # nothing ever read it — every login silently got Django's
            # default 2-week persistent session regardless of whether
            # the box was checked. Now an unchecked box actually
            # expires the session when the browser closes.
            if not request.POST.get('remember_me'):
                request.session.set_expiry(0)
            next_url = request.GET.get('next', 'home')
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect(next_url)
        else:
            record_attempt(request, 'login', window_seconds=300)
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
    orders = request.user.order_set.all()[:5]
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
    if is_rate_limited(request, 'newsletter', max_attempts=10, window_seconds=3600):
        return JsonResponse({'status': 'error', 'message': 'Too many attempts. Please try again later.'}, status=429)
    record_attempt(request, 'newsletter', window_seconds=3600)
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

    def post(self, request, *args, **kwargs):
        # Guards against using this form to spam an inbox with reset
        # emails, or to enumerate which emails have accounts (timing/
        # side-channel aside, the response is already identical either
        # way — this just stops volume abuse).
        if is_rate_limited(request, 'password_reset', max_attempts=5, window_seconds=3600):
            messages.error(request, 'Too many reset requests. Please try again later.')
            return redirect('password_reset')
        record_attempt(request, 'password_reset', window_seconds=3600)
        return super().post(request, *args, **kwargs)


class SarabPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = '/accounts/login/'
