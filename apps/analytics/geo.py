"""
geo.py — IP to country lookup utility.
Uses MaxMind GeoLite2-Country database if available.
Falls back to a simple country code without lookup.

To get the free database:
1. Register at https://www.maxmind.com/en/geolite2/signup
2. Download GeoLite2-Country.mmdb
3. Place it in ~/envs/django_project/geoip/GeoLite2-Country.mmdb
"""

import os
from django.conf import settings


def get_country_code(ip_address):
    """
    Returns 2-letter ISO country code for an IP address.
    Returns 'XX' if lookup fails or database not available.
    """
    if not ip_address or ip_address in ('127.0.0.1', '::1', '0.0.0.0'):
        return 'LC'  # Local / development

    db_path = os.path.join(settings.GEOIP_PATH, 'GeoLite2-Country.mmdb')

    if not os.path.exists(db_path):
        # Database not downloaded yet — return unknown
        return 'XX'

    try:
        import geoip2.database
        with geoip2.database.Reader(db_path) as reader:
            response = reader.country(ip_address)
            return response.country.iso_code or 'XX'
    except Exception:
        return 'XX'
