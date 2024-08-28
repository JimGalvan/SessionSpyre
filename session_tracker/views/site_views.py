from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from session_tracker.models import Site


@login_required
def list_sites(request):
    sites = Site.objects.filter(user=request.user)
    return render(request, 'sessions/list_sites.html', {'sites': sites})


# views.py (excerpt)

@login_required
def create_site(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        domain = request.POST.get('domain')

        # Check if the user has reached the site limit
        if Site.objects.filter(user=request.user).count() >= 3:
            messages.error(request, "You have reached the limit of 3 sites.")
            return redirect(reverse('list_sites'))

        # Check for domain uniqueness
        if Site.objects.filter(domain=domain).exists():
            messages.error(request, "A site with this domain already exists.")
            return redirect(reverse('create_site'))

        Site.objects.create(user=request.user, name=name, domain=domain)
        messages.success(request, "Site created successfully!")
        return redirect(reverse('list_sites'))

    return render(request, 'sites/create_site.html')


@login_required
def update_site(request, site_id):
    site = get_object_or_404(Site, id=site_id, user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name')
        site.name = name
        site.save()
        messages.success(request, "Site updated successfully!")
        return redirect(reverse('list_sites'))

    return render(request, 'sites/update_site.html', {'site': site})


@login_required
def delete_site(request, site_id):
    site = get_object_or_404(Site, id=site_id, user=request.user)
    if request.method == 'POST':
        site.delete()
        messages.success(request, "Site deleted successfully!")
        return redirect(reverse('list_sites'))

    return render(request, 'sites/delete_site.html', {'site': site})
