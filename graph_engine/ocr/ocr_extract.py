
import io
import os
import re
import sys

import requests
from PIL import Image

_OCRSPACE_ENDPOINT = "https://api.ocr.space/parse/image"
_KEY_FILE = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), ".ocrspace_key.txt")

# engine 3

_EXTENDED_TO_STANDARD_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩")

# Arabic diacritics (tashkeel/harakat) + tatweel (the elongation dash) —
# stripped
_DIACRITICS_RE = re.compile(
    r"[ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۨ-ۭـ]"
)


def normalize_digits(text):
    return text.translate(_EXTENDED_TO_STANDARD_DIGITS)


def strip_diacritics(text):
    return _DIACRITICS_RE.sub("", text)


def _tidy(text):
    """Drop blank lines and lines that are pure noise (no actual letters)."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if re.search(r"[؀-ۿ A-Za-z]", ln)]
    return "\n".join(lines)


def _resolve_api_key(api_key):
    if api_key:
        return api_key
    if os.environ.get("OCRSPACE_API_KEY"):
        return os.environ["OCRSPACE_API_KEY"]
    if os.path.isfile(_KEY_FILE):
        with open(_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    raise RuntimeError(
        "No OCR.space API key found. Pass api_key=..., set the "
        "OCRSPACE_API_KEY environment variable, or put the key in "
        f"{_KEY_FILE} — see graph_engine/ocr/README.md."
    )


def _load_image(image):
    """Accepts a file path, raw bytes, a file-like object, or a PIL Image."""
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, (bytes, bytearray)):
        return Image.open(io.BytesIO(image))
    if hasattr(image, "read"):
        return Image.open(image)
    return Image.open(image)  # path-like


def _image_to_jpeg_bytes(pil_image):
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def extract_text_from_image(image, api_key=None, engine=3, strip_tashkeel=True):

    api_key = _resolve_api_key(api_key)
    pil_image = _load_image(image)
    jpeg_bytes = _image_to_jpeg_bytes(pil_image)

    resp = requests.post(
        _OCRSPACE_ENDPOINT,
        data={
            "apikey": api_key,
            "language": "ara",
            "OCREngine": engine,
            "scale": "true",
            "isOverlayRequired": "false",
        },
        files={"file": ("image.jpg", jpeg_bytes, "image/jpeg")},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("IsErroredOnProcessing"):
        raise RuntimeError(f"OCR.space error: {result.get('ErrorMessage')}")

    parsed = result.get("ParsedResults") or []
    text = parsed[0].get("ParsedText", "") if parsed else ""
    text = normalize_digits(text)
    if strip_tashkeel:
        text = strip_diacritics(text)
    text = _tidy(text)
    return text.strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ocr_extract.py <image_path>")
        sys.exit(1)
    print(extract_text_from_image(sys.argv[1]))
