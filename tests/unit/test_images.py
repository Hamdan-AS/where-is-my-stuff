"""Unit tests for ``core.images``: resize, flatten, orient, and re-encode photos."""

from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.images import MAX_EDGE, normalize_photo


def upload(image, *, name="item.png", image_format="PNG", **save_kwargs):
    buffer = BytesIO()
    image.save(buffer, format=image_format, **save_kwargs)
    content_type = "image/jpeg" if image_format == "JPEG" else "image/png"
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def normalized_image(source):
    return Image.open(BytesIO(normalize_photo(source).read()))


class OutputFormatTests(SimpleTestCase):
    def test_the_result_is_a_jpeg_content_file(self):
        result = normalize_photo(upload(Image.new("RGB", (80, 60), "blue")))
        self.assertEqual(result.name, "item-photo.jpg")
        data = result.read()
        self.assertTrue(data.startswith(b"\xff\xd8"))
        self.assertTrue(data.endswith(b"\xff\xd9"))

    def test_the_result_can_be_opened_and_is_rgb(self):
        with normalized_image(upload(Image.new("RGB", (80, 60), "blue"))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.mode, "RGB")

    def test_every_call_returns_a_new_content_file(self):
        source = upload(Image.new("RGB", (32, 32), "green"))
        first = normalize_photo(source)
        source.seek(0)
        second = normalize_photo(source)
        self.assertIsNot(first, second)
        self.assertEqual(first.read(), second.read())


class SourcePositionTests(SimpleTestCase):
    def test_the_upload_is_read_from_the_beginning_even_if_already_read(self):
        source = upload(Image.new("RGB", (64, 48), "red"))
        source.read(20)
        with normalized_image(source) as image:
            self.assertEqual(image.size, (64, 48))


class ResizeTests(SimpleTestCase):
    def test_a_small_photo_is_not_stretched(self):
        with normalized_image(upload(Image.new("RGB", (100, 50)))) as image:
            self.assertEqual(image.size, (100, 50))
            self.assertLessEqual(max(image.size), MAX_EDGE)

    def test_a_wide_photo_is_scaled_to_the_maximum_long_edge(self):
        with normalized_image(upload(Image.new("RGB", (3000, 1000)))) as image:
            self.assertEqual(image.size, (1800, 600))

    def test_a_tall_photo_is_scaled_to_the_maximum_long_edge(self):
        with normalized_image(upload(Image.new("RGB", (1000, 3000)))) as image:
            self.assertEqual(image.size, (600, 1800))

    def test_a_square_photo_is_scaled_to_the_maximum_long_edge(self):
        with normalized_image(upload(Image.new("RGB", (4000, 4000)))) as image:
            self.assertEqual(image.size, (1800, 1800))

    def test_the_long_edge_limit_is_1800_pixels(self):
        self.assertEqual(MAX_EDGE, 1800)

    def test_the_whole_photo_is_kept_rather_than_cropped(self):
        with normalized_image(upload(Image.new("RGB", (2000, 1000)))) as image:
            self.assertEqual(image.size, (1800, 900))


class TransparencyTests(SimpleTestCase):
    def test_transparent_areas_are_flattened_onto_white(self):
        source = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        source.paste((220, 20, 20, 255), (0, 0, 10, 10))
        with normalized_image(upload(source)) as image:
            self.assertEqual(image.mode, "RGB")
            red = image.getpixel((5, 5))
            white = image.getpixel((19, 19))
            self.assertGreater(red[0], 200)
            self.assertLess(red[1], 80)
            self.assertGreater(white[0], 240)
            self.assertGreater(white[1], 240)
            self.assertGreater(white[2], 240)

    def test_a_palette_image_with_transparency_is_flattened(self):
        source = Image.new("P", (10, 10))
        source.putpalette([255, 0, 0, 0, 0, 0] + [0, 0, 0] * 254)
        source.info["transparency"] = 0
        with normalized_image(upload(source)) as image:
            self.assertEqual(image.mode, "RGB")

    def test_opaque_images_keep_their_colour(self):
        with normalized_image(upload(Image.new("RGB", (20, 20), (30, 160, 90)))) as image:
            pixel = image.getpixel((10, 10))
            self.assertLess(abs(pixel[0] - 30), 15)
            self.assertLess(abs(pixel[1] - 160), 15)
            self.assertLess(abs(pixel[2] - 90), 15)


class ModeTests(SimpleTestCase):
    def test_cmyk_images_are_converted_to_rgb(self):
        with normalized_image(upload(
            Image.new("CMYK", (20, 20), (0, 0, 0, 0)), image_format="JPEG",
        )) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertGreater(image.getpixel((10, 10))[0], 240)

    def test_greyscale_images_are_converted_to_rgb(self):
        with normalized_image(upload(Image.new("L", (20, 20), 128), image_format="JPEG")) as image:
            self.assertEqual(image.mode, "RGB")


class MetadataTests(SimpleTestCase):
    def test_exif_metadata_is_discarded(self):
        exif = Image.Exif()
        exif[274] = 1
        exif[271] = "Test Camera"
        source = upload(
            Image.new("RGB", (40, 30), "blue"),
            image_format="JPEG",
            exif=exif,
        )
        with normalized_image(source) as image:
            self.assertFalse(dict(image.getexif()))

    def test_exif_orientation_is_applied_before_the_metadata_is_dropped(self):
        exif = Image.Exif()
        exif[274] = 6  # Rotate 90 degrees clockwise for display.
        source = upload(
            Image.new("RGB", (100, 50), "blue"), image_format="JPEG", exif=exif,
        )
        with normalized_image(source) as image:
            self.assertEqual(image.size, (50, 100))
            self.assertNotIn(274, dict(image.getexif()))
