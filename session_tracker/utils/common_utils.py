# `session_tracker/utils/common_utils.py`
import pytz
from django.utils import timezone


def convert_utc_to_local(utc_dt, local_tz_str=None):
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)

    if local_tz_str is None:
        local_tz_str = timezone.get_current_timezone_name()

    local_tz = pytz.timezone(local_tz_str)
    return utc_dt.astimezone(local_tz)
