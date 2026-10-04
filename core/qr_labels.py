"""Helpers for stable, expiring personal-item QR labels."""
import calendar
import hashlib
import secrets

from django.utils import timezone

from .qr import generate_qr_png

ACTIVE_MONTHS = 6


def new_label_token():
    return secrets.token_urlsafe(32)


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def expiry_after_months(start, months=ACTIVE_MONTHS):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def make_label_qr(url):
    return generate_qr_png(url)
