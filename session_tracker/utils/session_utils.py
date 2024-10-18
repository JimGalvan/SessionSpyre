import re
from urllib.parse import urlparse

from session_tracker.models import Site, URLExclusionRule, UserSession


def get_client_ip(self):
    # Decode headers
    headers = dict((k.decode('utf-8'), v.decode('utf-8')) for k, v in self.scope['headers'])
    # Check for X-Forwarded-For header
    x_forwarded_for = headers.get('x-forwarded-for')
    if x_forwarded_for:
        # Multiple IPs can be in X-Forwarded-For header; the first is the client's IP
        ip = x_forwarded_for.split(',')[0]
    else:
        # Fallback to scope['client']
        ip = self.scope['client'][0]
    return ip


async def validate_site_key(site_id, site_key):
    """Validate if the provided site_key belongs to the site."""
    return await Site.objects.filter(id=site_id, key=site_key).afirst()


async def get_exclusion_rules(user_id, site_id):
    exclusion_rules_dtos = []
    async for rule in URLExclusionRule.objects.filter(user_id=user_id, site_id=site_id).all():
        exclusion_rules_dtos.append(
            URLExclusionRuleDto(
                domain=rule.domain,
                exclusion_type=rule.exclusion_type,
                url_pattern=rule.url_pattern,
                ip_address=rule.ip_address
            )
        )
    return exclusion_rules_dtos


def normalize_domain(domain: str) -> tuple[str, int]:
    # Ensure the domain has a scheme
    if not domain.startswith(('http://', 'https://')):
        domain = 'http://' + domain
    parsed_domain = urlparse(domain)
    return parsed_domain.hostname, parsed_domain.port


async def is_domain_or_subdomain_excluded(site_url: str, exclusion_rules: list) -> bool:
    parsed_url = urlparse(site_url)
    site_hostname = parsed_url.hostname

    if not site_hostname:
        return False

    for rule in exclusion_rules:
        rule_domain_hostname = None
        if rule.exclusion_type in ['domain', 'subdomain']:
            rule_domain_hostname, _ = normalize_domain(rule.domain)

        # Check if it's an exact domain match
        if rule.exclusion_type == 'domain' and re.fullmatch(re.escape(rule_domain_hostname), site_hostname):
            return True

        # Check if it's a subdomain match (e.g., sub.example.com should match *.example.com)
        elif rule.exclusion_type == 'subdomain':
            # Prepare regex for subdomain matching: match subdomains like *.example.com
            subdomain_pattern = r'\.?' + re.escape(rule_domain_hostname) + r'$'
            if re.search(subdomain_pattern, site_hostname):
                return True
    return False


async def is_url_pattern_excluded(url: str, exclusion_rules: list) -> bool:
    # Extract path from the full URL, in case a full URL is passed
    parsed_url = urlparse(url)
    url = parsed_url.path

    for rule in exclusion_rules:
        if rule.exclusion_type == 'url_pattern' and rule.url_pattern:
            # Convert wildcard pattern to regular expression
            # Replace '*' with '.*' for wildcard support and escape the rest
            pattern = re.escape(rule.url_pattern).replace(r'\*', '.*')
            # Ensure full match by anchoring the pattern at start and end
            pattern = f"^{pattern}$"

            # Perform regex match
            if re.match(pattern, url):
                return True
    return False


async def is_session_id_valid(session_id, site_id):
    """Check if the session ID is valid."""

    # Check if the session ID is not None
    if not session_id:
        return False

    # Check if the session ID is not empty
    if not session_id.strip():
        return False

    # Check if the session ID is not too long
    if len(session_id) > 255:
        return False

    # Check if session id does not belong to the current site
    if not await UserSession.objects.filter(id=session_id, site_id=site_id).aexists():
        return False

    return True


async def is_ip_excluded(ip_address, exclusion_rules):
    for rule in exclusion_rules:
        if rule.exclusion_type == 'ip_address' and rule.ip_address == ip_address:
            return True
    return False


class URLExclusionRuleDto:
    def __init__(self, domain=None, exclusion_type=None, url_pattern=None, ip_address=None):
        self.domain = domain
        self.exclusion_type = exclusion_type
        self.url_pattern = url_pattern
        self.ip_address = ip_address
