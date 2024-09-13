import pytest

from session_tracker.consumers import is_domain_or_subdomain_excluded
from session_tracker.tests.ExclusionRule import ExclusionRule


@pytest.mark.asyncio
@pytest.mark.django_db
class TestIsDomainOrSubdomainExcluded:
    # Positive Test Cases
    async def test_is_domain_excluded_positive(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', domain='example.com')]
        site_url = 'http://example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == True

    async def test_is_subdomain_excluded_positive(self):
        exclusion_rules = [ExclusionRule(exclusion_type='subdomain', domain='example.com')]
        site_url = 'http://sub.example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == True

    async def test_is_subdomain_excluded_with_domain(self):
        exclusion_rules = [ExclusionRule(exclusion_type='subdomain', domain='example.com')]
        site_url = 'http://example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == True

    async def test_is_subdomain_excluded_multiple_subdomains(self):
        exclusion_rules = [ExclusionRule(exclusion_type='subdomain', domain='example.com')]
        site_url = 'http://sub.sub.example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == True

    # Negative Test Cases
    async def test_is_domain_excluded_negative(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', domain='example.com')]
        site_url = 'http://notexample.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    async def test_is_subdomain_excluded_negative(self):
        exclusion_rules = [ExclusionRule(exclusion_type='subdomain', domain='example.com')]
        site_url = 'http://example.org'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    async def test_is_subdomain_excluded_negative_other_domain(self):
        exclusion_rules = [ExclusionRule(exclusion_type='subdomain', domain='other.com')]
        site_url = 'http://example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    async def test_is_domain_excluded_subdomain_negative(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', domain='example.com')]
        site_url = 'http://sub.example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    async def test_is_domain_or_subdomain_excluded_wrong_exclusion_type(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', domain='example.com')]
        site_url = 'http://example.com'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    # Edge Cases
    async def test_is_domain_or_subdomain_excluded_no_hostname(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', domain='example.com')]
        site_url = 'not a valid url'
        result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
        assert result == False

    async def test_is_domain_or_subdomain_excluded_rule_domain_none(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', domain=None)]
        site_url = 'http://example.com'
        with pytest.raises(AttributeError):
            result = await is_domain_or_subdomain_excluded(site_url, exclusion_rules)
