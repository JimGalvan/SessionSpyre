import pytz


def convert_utc_to_local(utc_dt, local_tz_str):
    # Ensure the input datetime is timezone-aware
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)

    # Get the local timezone
    local_tz = pytz.timezone(local_tz_str)

    # Convert the UTC datetime to the local timezone
    local_dt = utc_dt.astimezone(local_tz)

    return local_dt
