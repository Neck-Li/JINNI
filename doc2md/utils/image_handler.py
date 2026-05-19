from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image as PILImage


def save_image(
    image_data: bytes,
    output_dir: str,
    alt_text: str = "",
    index: int = 0,
) -> str:
    """Save image bytes to disk and return relative path for Markdown.

    Returns the markdown image string: ![alt](path)
    """
    img_dir = Path(output_dir) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    ext = _detect_format(image_data)
    digest = hashlib.md5(image_data).hexdigest()[:12]
    filename = f"img_{index:04d}_{digest}.{ext}"
    path = img_dir / filename

    if not path.exists():
        with open(path, "wb") as f:
            f.write(image_data)

    rel = f"images/{filename}"
    alt = alt_text or f"image-{index}"
    return f"![{alt}]({rel})"


def _detect_format(data: bytes) -> str:
    """Detect image format from magic bytes."""
    if data.startswith(b"\xff\xd8"):
        return "jpg"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"GIF8"):
        return "gif"
    if data.startswith(b"WEBP"):
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"\x49\x49\x2a\x00") or data.startswith(b"\x4d\x4d\x00\x2a"):
        return "tiff"
    return "png"


def extract_images_from_pdf(page, doc_path: str) -> list[tuple[bytes, str]]:
    """Extract images from a PDF page using PyMuPDF."""
    images = []
    try:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_image = doc_path.extract_image(xref)
            images.append((base_image["image"], "image"))
    except Exception:
        pass
    return images
