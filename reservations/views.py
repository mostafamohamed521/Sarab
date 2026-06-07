from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Reservation
from .forms import ReservationForm
import json


def make_reservation(request):
    if request.method == 'POST':
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
    reservation = get_object_or_404(Reservation, confirmation_code=code)
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
