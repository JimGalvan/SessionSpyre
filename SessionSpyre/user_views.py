from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import RegisterForm


def index(request):
    return render(request, 'index.html')


class Login(LoginView):
    template_name = 'user/login.html'

    def form_invalid(self, form):
        # Add a non-field error
        form.add_error(None, "Incorrect username or password.")
        return super().form_invalid(form)


class RegisterView(FormView):
    form_class = RegisterForm
    template_name = 'user/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()  # save the user
        return super().form_valid(form)


@login_required
def profile_view(request):
    return render(request, 'user/profile.html')
