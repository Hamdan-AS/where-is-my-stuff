"""Unit tests for ``core.qr``: the PNG encoder used by report and label codes."""

from io import BytesIO

from PIL import Image
from django.test import SimpleTestCase

from core.qr import generate_qr_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class GenerateQRPngTests(SimpleTestCase):
    def test_the_result_is_a_buffer_rewound_to_the_start(self):
        result = generate_qr_png("https://example.test/r/abc/found/")
        self.assertIsInstance(result, BytesIO)
        self.assertEqual(result.tell(), 0)

    def test_the_result_is_a_real_png(self):
        data = generate_qr_png("https://example.test/r/abc/found/").getvalue()
        self.assertTrue(data.startswith(PNG_SIGNATURE))
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertGreater(image.width, 0)
            self.assertGreater(image.height, 0)

    def test_the_code_is_square(self):
        with Image.open(generate_qr_png("https://example.test/tag/token/")) as image:
            self.assertEqual(image.width, image.height)

    def test_different_urls_produce_different_codes(self):
        first = generate_qr_png("https://example.test/tag/one/").getvalue()
        second = generate_qr_png("https://example.test/tag/two/").getvalue()
        self.assertNotEqual(first, second)

    def test_the_same_url_is_encoded_stably(self):
        first = generate_qr_png("https://example.test/tag/same/").getvalue()
        second = generate_qr_png("https://example.test/tag/same/").getvalue()
        self.assertEqual(first, second)

    def test_a_long_url_still_fits(self):
        url = "https://example.test/" + ("very-long-path/" * 40)
        data = generate_qr_png(url).getvalue()
        self.assertTrue(data.startswith(PNG_SIGNATURE))

    def test_each_call_returns_an_independent_buffer(self):
        first = generate_qr_png("https://example.test/tag/one/")
        second = generate_qr_png("https://example.test/tag/one/")
        self.assertIsNot(first, second)
        first.read()
        self.assertEqual(second.tell(), 0)
