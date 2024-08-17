from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__exact=username).exists():
            raise forms.ValidationError(f"The username {username} is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__exact=email).exists():
            raise forms.ValidationError(f"The email {email} is already in use.")
        return email
