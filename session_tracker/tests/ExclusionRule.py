# Mock the ExclusionRule class
class ExclusionRule:
    def __init__(self, exclusion_type, domain=None, url_pattern=None):
        self.exclusion_type = exclusion_type
        self.domain = domain
        self.url_pattern = url_pattern
