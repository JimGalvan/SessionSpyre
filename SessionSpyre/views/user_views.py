import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import FormView

from SessionSpyre.forms import UserProfileForm, RegisterForm


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


@login_required
def update_timezone(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to a profile page or any other page
    else:
        form = UserProfileForm(instance=request.user.userprofile)

    return render(request, 'user/profile.html', {'form': form})


@login_required
def set_timezone(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        timezone = data.get('timezone', None)
        if timezone:
            request.session['django_timezone'] = timezone  # Save to session
            # Alternatively, save to user profile if user is authenticated
            if request.user.is_authenticated:
                request.user.userprofile.timezone = timezone
                request.user.userprofile.save()
        return JsonResponse({'status': 'success', 'timezone': timezone})
    return JsonResponse({'status': 'failed'}, status=400)
