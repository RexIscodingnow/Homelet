import os
from datetime import datetime
from zoneinfo import ZoneInfo

from suntime import Sun


ALLOWED_EXTENSIONS = ('png', 'jpg', 'jpeg', 'gif', 'webp')


def allowed_file(filename: str):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_files_in_dir(dir: str):
    return [filename for filename in os.listdir(dir) if filename.lower().endswith(ALLOWED_EXTENSIONS)]


def get_sun_times(lat: float = 25.0330, lng: float = 121.5654):
    sun = Sun(lat, lng)

    today = datetime.now()
    sunrise_utc = sun.get_sunrise_time(today)
    sunset_utc = sun.get_sunset_time(today)

    taipei_tz = ZoneInfo("Asia/Taipei")
    sunrise_t = sunrise_utc.astimezone(taipei_tz)
    sunset_t = sunset_utc.astimezone(taipei_tz)

    print(f"Sunrise: {sunrise_t.strftime('%Y-%m-%d %H:%M:%S')}\n" \
          f" Sunset: {sunset_t.strftime('%Y-%m-%d %H:%M:%S')}")

    return sunrise_t, sunset_t
