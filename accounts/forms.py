from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from .models import CustomUser, Address


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'fctrl'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'fctrl'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'fctrl'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'fctrl'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'fctrl'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'fctrl'}))

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'fctrl', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'fctrl'}))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'bio', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'fctrl'}),
            'last_name': forms.TextInput(attrs={'class': 'fctrl'}),
            'phone': forms.TextInput(attrs={'class': 'fctrl'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'fctrl', 'type': 'date'}),
            'bio': forms.Textarea(attrs={'class': 'fctrl', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'fctrl'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['label', 'full_name', 'phone', 'street_address', 'city', 'state', 'zip_code', 'country', 'is_default']
        widgets = {
            'label': forms.Select(attrs={'class': 'fctrl'}),
            'full_name': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'Phone Number'}),
            'street_address': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'State'}),
            'zip_code': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'ZIP Code'}),
            'country': forms.TextInput(attrs={'class': 'fctrl', 'placeholder': 'Country'}),
        }


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'fctrl', 'placeholder': 'Enter your email address'}))


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'fctrl', 'placeholder': 'New Password'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'fctrl', 'placeholder': 'Confirm New Password'}))
