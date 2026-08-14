from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from .models import Reservation
from .forms import ReservationForm
from config.ratelimit import is_rate_limited, record_attempt
import json


def make_reservation(request):
    if request.method == 'POST':
        if is_rate_limited(request, 'reservation', max_attempts=10, window_seconds=3600):
            message = 'Too many reservation attempts. Please try again later.'
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': message}, status=429)
            messages.error(request, message)
            return render(request, 'reservations/make_reservation.html', {'form': ReservationForm()})
        record_attempt(request, 'reservation', window_seconds=3600)
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                form = ReservationForm(data)
            else:
                form = ReservationForm(request.POST)
        except Exception:
            form = ReservationForm(request.POST)

        if form.is_valid():
            reservation = form.save(commit=False)
            if request.user.is_authenticated:
                reservation.user = request.user
            reservation.save()
            if request.content_type == 'application/json':
                return JsonResponse({
                    'status': 'ok',
                    'confirmation_code': reservation.confirmation_code,
                    'message': "Table reserved! We'll confirm via email shortly.",
                })
            messages.success(request, f'Reservation confirmed! Your code: {reservation.confirmation_code}')
            return redirect('reservation_confirmation', code=reservation.confirmation_code)
        else:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ReservationForm()
    return render(request, 'reservations/make_reservation.html', {'form': form})


def reservation_confirmation(request, code):
    """
    A guest reservation (no account) has no owner to check against —
    the confirmation code itself is the credential, same as most
    restaurant booking systems, and that's intentional.

    But once a reservation is attached to a logged-in account, it
    carries that customer's name/email/phone, so it must not be
    viewable by a different account just from knowing/guessing the
    code (IDOR).
    """
    reservation = get_object_or_404(Reservation, confirmation_code=code)
    if reservation.user_id is not None:
        if not request.user.is_authenticated or request.user.pk != reservation.user_id:
            return HttpResponseForbidden("You do not have permission to view this reservation.")
    return render(request, 'reservations/confirmation.html', {'reservation': reservation})


@login_required
def reservation_history(request):
    reservations = request.user.reservations.all()
    return render(request, 'reservations/history.html', {'reservations': reservations})


@login_required
def cancel_reservation(request, code):
    reservation = get_object_or_404(Reservation, confirmation_code=code, user=request.user)
    if request.method == 'POST':
        reservation.status = Reservation.STATUS_CANCELLED
        reservation.save()
        messages.success(request, 'Reservation cancelled.')
    return redirect('reservation_history')
