import pytz
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile, UserAccount


class RegisterForm(UserCreationForm):
    class Meta:
        model = UserAccount
        fields = ["username", "email", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data['username']
        if UserAccount.objects.filter(username__exact=username).exists():
            raise forms.ValidationError(f"The username {username} is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if UserAccount.objects.filter(email__exact=email).exists():
            raise forms.ValidationError(f"The email {email} is already in use.")
        return email


class UserProfileForm(forms.ModelForm):
    timezone = forms.ChoiceField(choices=[(tz, tz) for tz in pytz.all_timezones],
                                 widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = UserProfile
        fields = ['timezone']
