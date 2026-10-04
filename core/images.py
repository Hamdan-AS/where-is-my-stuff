"""Normalize user supplied item photos before keeping or serving them."""
from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.base import ContentFile

MAX_EDGE = 1800


def normalize_photo(upload):
    """Keep the whole photo, resize its longest edge, and discard metadata."""
    upload.seek(0)
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, "white")
            flattened.paste(rgba, mask=rgba.getchannel("A"))
            image = flattened
        else:
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=86, optimize=True)
    return ContentFile(output.getvalue(), name="item-photo.jpg")
