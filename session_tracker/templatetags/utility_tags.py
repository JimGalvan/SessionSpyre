from django import template

from session_tracker.utils.common_utils import convert_utc_to_local

register = template.Library()


@register.filter(name='convert_utc_to_local')
def convert_utc_to_local_filter(value, local_tz_str):
    return convert_utc_to_local(value, local_tz_str)
