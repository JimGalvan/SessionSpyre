import pytest

from session_tracker.consumers import is_url_pattern_excluded
from session_tracker.tests.ExclusionRule import ExclusionRule


@pytest.mark.asyncio
@pytest.mark.django_db
class TestIsUrlPatternExcluded:
    # Positive Test Cases
    async def test_is_url_pattern_excluded_positive(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/admin/*')]
        url = '/admin/dashboard'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True

    async def test_is_url_pattern_excluded_with_full_url(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/admin/*')]
        url = 'http://example.com/admin/dashboard'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True

    async def test_is_url_pattern_excluded_exact_match(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/admin')]
        url = '/admin'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True

    async def test_is_url_pattern_excluded_multiple_wildcards(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/product/*/details')]
        url = '/product/123/details'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True

    # Negative Test Cases
    async def test_is_url_pattern_excluded_negative(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/admin/*')]
        url = '/user/profile'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False

    async def test_is_url_pattern_excluded_multiple_wildcards_negative(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/product/*/details')]
        url = '/product/123/overview'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False

    async def test_is_url_pattern_excluded_regex_characters_in_pattern(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/user/([0-9]+)')]
        url = '/user/12345'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False  # Special regex characters are escaped

    # Edge Cases
    async def test_is_url_pattern_excluded_rule_pattern_none(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern=None)]
        url = '/admin/dashboard'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False

    async def test_is_url_pattern_excluded_wrong_exclusion_type(self):
        exclusion_rules = [ExclusionRule(exclusion_type='domain', url_pattern='/admin/*')]
        url = '/admin/dashboard'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False

    async def test_is_url_pattern_excluded_with_query_params(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/search')]
        url = '/search?q=test'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True  # Query parameters are ignored

    async def test_is_url_pattern_excluded_empty_url(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/')]
        url = ''
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == False

    # Special Characters Handling
    async def test_is_url_pattern_excluded_special_characters_wildcard(self):
        exclusion_rules = [ExclusionRule(exclusion_type='url_pattern', url_pattern='/user/*')]
        url = '/user/.abc'
        result = await is_url_pattern_excluded(url, exclusion_rules)
        assert result == True
