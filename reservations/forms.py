from django import forms
from .models import Reservation
from datetime import date

GUESTS_CHOICES = [
    (1, '1 Person'), (2, '2 People'), (4, '3-4 People'),
    (6, '5-6 People'), (8, '7-8 People'), (10, '10+ People'),
]
TIME_CHOICES = [
    ('09:00', '09:00 AM'), ('10:00', '10:00 AM'), ('11:00', '11:00 AM'),
    ('12:00', '12:00 PM'), ('13:00', '01:00 PM'), ('14:00', '02:00 PM'),
    ('18:00', '06:00 PM'), ('19:00', '07:00 PM'), ('20:00', '08:00 PM'),
    ('21:00', '09:00 PM'), ('22:00', '10:00 PM'),
]


class ReservationForm(forms.ModelForm):
    time = forms.ChoiceField(choices=TIME_CHOICES, widget=forms.Select(attrs={'class': 'fctrl'}))
    guests = forms.ChoiceField(choices=GUESTS_CHOICES, widget=forms.Select(attrs={'class': 'fctrl'}))

    class Meta:
        model = Reservation
        fields = ['full_name', 'email', 'phone', 'guests', 'date', 'time', 'occasion', 'special_requests']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'John Doe'}),
            'email': forms.EmailInput(attrs={'class': 'fctrl', 'placeholder': 'you@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': '+1 (800) 000-0000'}),
            'date': forms.DateInput(attrs={'class': 'fctrl', 'type': 'date', 'min': str(date.today())}),
            'occasion': forms.Select(attrs={'class': 'fctrl'}),
            'special_requests': forms.Textarea(attrs={'class': 'fctrl', 'rows': 3}),
        }

    def clean_date(self):
        # The HTML `min` attribute above is client-side only — a direct
        # POST (or a modified request) could otherwise book a date in
        # the past.
        value = self.cleaned_data['date']
        if value < date.today():
            raise forms.ValidationError('Reservation date cannot be in the past.')
        return value
