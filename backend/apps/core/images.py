"""Shared upload hardening for user-supplied images (avatars, course covers)."""

# Magic-byte signatures — the Content-Type header is client-controlled and
# trivially spoofed, so we sniff the actual file header instead.
_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # RIFF....WEBP — verified below
}


def sniff_image_type(header: bytes) -> str | None:
    """Return a safe extension when `header` is a real raster image, else None."""
    for signature, ext in _IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            if ext == "webp" and header[8:12] != b"WEBP":
                continue
            return ext
    return None
