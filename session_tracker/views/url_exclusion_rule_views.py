from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST, require_http_methods

from session_tracker.models import Site, URLExclusionRule


@login_required
@require_GET
def get_url_exclusions(request, site_id):
    site = get_object_or_404(Site, id=site_id, user=request.user)
    exclusion_rules = URLExclusionRule.objects.filter(site=site)

    paginator = Paginator(exclusion_rules, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'exclusion_rules/url_exclusion_list.html', {
        'page_obj': page_obj,
        'site': site
    })


@login_required
@require_POST
def add_url_exclusion(request, site_id):
    site = get_object_or_404(Site, id=site_id, user=request.user)
    url_pattern = request.POST.get('url_pattern')

    if not url_pattern:
        return HttpResponseBadRequest("URL pattern is required")

    # Create and save the exclusion rule
    URLExclusionRule.objects.create(site=site, user=request.user, url_pattern=url_pattern)

    # Return the updated list of rules as a partial HTML to be swapped in HTMX
    exclusion_rules = URLExclusionRule.objects.filter(site=site)

    paginator = Paginator(exclusion_rules, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'exclusion_rules/url_exclusion_list.html', {
        'page_obj': page_obj,
        'site': site
    })


@login_required
@require_http_methods(["DELETE"])
def delete_url_exclusion(request, rule_id):
    rule = get_object_or_404(URLExclusionRule, id=rule_id, user=request.user)
    rule.delete()

    # Return the updated list of rules as a partial HTML to be swapped in HTMX
    exclusion_rules = URLExclusionRule.objects.filter(site=rule.site)

    paginator = Paginator(exclusion_rules, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'exclusion_rules/url_exclusion_list.html', {
        'page_obj': page_obj,
    })
