from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import JavascriptLexer

from session_tracker.models import Site


@login_required
@require_GET
def generate_snippet(request, user_id, site_id):
    try:
        # Fetch the site key from the database
        site = Site.objects.get(id=site_id, user_id=user_id)
        site_key = site.key  # Assuming 'site_key' is a field in your Site model

        # Construct the snippet
        snippet = f"""
               <script src="https://your-cdn-url.com/your-script.js"></script>
               <script>
                 (function() {{
                   window.recordConfig = {{
                     userId: '{user_id}',
                     siteId: '{site_id}',
                     siteKey: '{site_key}',
                   }};
                 }})();
               </script>
               """

        # Highlight the snippet using Pygments
        formatter = HtmlFormatter(full=True, style="dracula", noclasses=False, linenos=True)
        highlighted_snippet = highlight(snippet, JavascriptLexer(), formatter)
        return render(request, 'sites/js_snippet_dialog.html', {'highlighted_snippet': highlighted_snippet})
    except Site.DoesNotExist:
        return JsonResponse({'error': 'Site not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_snippet_data(request, user_id, site_id):
    try:
        # Fetch the site key from the database
        site = Site.objects.get(id=site_id, user_id=user_id)
        site_key = site.key  # Assuming 'site_key' is a field in your Site model

        # Build a snippet object
        snippet = {
            'userId': user_id,
            'siteId': site_id,
            'siteKey': site_key,
        }

        return render(request, 'sites/js_snippet.html', {'snippet': snippet})
    except Site.DoesNotExist:
        return JsonResponse({'error': 'Site not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required()
def sites_view(request):
    sites = Site.objects.filter(user=request.user)
    return render(request, 'sites/sites.html', {'sites': sites})


@login_required
def list_sites(request):
    sites = Site.objects.filter(user=request.user)
    return render(request, 'sites/list_sites.html', {'sites': sites})


@login_required
def create_site(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        domain = request.POST.get('domain')

        if domain is None or domain == '':
            domain = ""

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
    if request.method == 'DELETE':
        site.delete()
        messages.success(request, "Site deleted successfully!")
        return redirect(reverse('list_sites'))

    return render(request, 'sites/delete_site.html', {'site': site})
