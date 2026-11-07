"""Unit tests for ``core.qr_labels``: token, digest, expiry, and QR helpers."""

import hashlib
from datetime import date, datetime, timedelta, timezone as datetime_timezone

from PIL import Image
from django.test import SimpleTestCase
from django.utils import timezone

from core.qr_labels import (
    ACTIVE_MONTHS,
    expiry_after_months,
    make_label_qr,
    new_label_token,
    token_digest,
)


class TokenTests(SimpleTestCase):
    def test_each_token_is_unique(self):
        tokens = {new_label_token() for _ in range(50)}
        self.assertEqual(len(tokens), 50)

    def test_tokens_are_url_safe_text(self):
        for _ in range(20):
            token = new_label_token()
            self.assertTrue(token)
            self.assertTrue(all(character.isalnum() or character in "-_" for character in token))

    def test_the_default_token_has_256_bits_of_source_entropy(self):
        # token_urlsafe(32) encodes 32 bytes into 43 URL-safe characters.
        self.assertEqual(len(new_label_token()), 43)


class DigestTests(SimpleTestCase):
    def test_the_digest_is_the_sha256_hex_of_the_token(self):
        token = "a-known-token"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        self.assertEqual(token_digest(token), expected)
        self.assertEqual(len(token_digest(token)), 64)

    def test_the_digest_is_stable_and_token_specific(self):
        first = token_digest("first-token")
        self.assertEqual(first, token_digest("first-token"))
        self.assertNotEqual(first, token_digest("second-token"))

    def test_the_hash_does_not_contain_the_token(self):
        token = "plain-token-value"
        self.assertNotIn(token, token_digest(token))

    def test_unicode_tokens_are_hashed_as_utf8(self):
        token = "token-\u00e9"
        self.assertEqual(
            token_digest(token),
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )


class ExpiryTests(SimpleTestCase):
    def test_the_active_period_is_six_months(self):
        self.assertEqual(ACTIVE_MONTHS, 6)

    def test_six_months_are_added_within_the_same_year(self):
        self.assertEqual(expiry_after_months(date(2026, 1, 15)), date(2026, 7, 15))

    def test_december_rolls_over_into_the_next_year(self):
        self.assertEqual(expiry_after_months(date(2026, 12, 15)), date(2027, 6, 15))

    def test_the_day_is_clamped_to_the_end_of_the_target_month(self):
        self.assertEqual(expiry_after_months(date(2026, 8, 31)), date(2027, 2, 28))
        self.assertEqual(expiry_after_months(date(2023, 8, 31)), date(2024, 2, 29))

    def test_the_day_is_kept_when_the_target_month_is_long_enough(self):
        self.assertEqual(expiry_after_months(date(2026, 8, 30)), date(2027, 2, 28))
        self.assertEqual(expiry_after_months(date(2026, 1, 31)), date(2026, 7, 31))

    def test_other_periods_are_supported(self):
        self.assertEqual(expiry_after_months(date(2026, 1, 31), months=1), date(2026, 2, 28))
        self.assertEqual(expiry_after_months(date(2026, 1, 15), months=12), date(2027, 1, 15))
        self.assertEqual(expiry_after_months(date(2026, 1, 15), months=0), date(2026, 1, 15))

    def test_times_and_time_zones_are_preserved(self):
        start = datetime(2026, 8, 31, 13, 45, 30, tzinfo=datetime_timezone.utc)
        result = expiry_after_months(start)
        self.assertEqual(result.tzinfo, datetime_timezone.utc)
        self.assertEqual((result.hour, result.minute, result.second), (13, 45, 30))
        self.assertEqual(result.date(), date(2027, 2, 28))

    def test_the_common_case_uses_the_current_time_zone(self):
        start = timezone.now()
        self.assertEqual(expiry_after_months(start).tzinfo, start.tzinfo)
        self.assertGreater(expiry_after_months(start), start)


class LabelQRTests(SimpleTestCase):
    def test_labels_use_the_shared_qr_encoder(self):
        data = make_label_qr("https://example.test/tag/token/").getvalue()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(make_label_qr("https://example.test/tag/token/")) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.width, image.height)

    def test_two_labels_for_different_urls_differ(self):
        first = make_label_qr("https://example.test/tag/one/").getvalue()
        second = make_label_qr("https://example.test/tag/two/").getvalue()
        self.assertNotEqual(first, second)

    def test_the_label_qr_is_independent_of_the_report_qr_helper(self):
        from core.qr import generate_qr_png

        url = "https://example.test/tag/token/"
        self.assertEqual(make_label_qr(url).getvalue(), generate_qr_png(url).getvalue())


class ExpiryDurationTests(SimpleTestCase):
    def test_expiry_is_in_the_future_for_a_current_label(self):
        now = timezone.now()
        self.assertGreater(expiry_after_months(now), now + timedelta(days=150))
