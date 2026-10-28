import hashlib
import re
from typing import BinaryIO, Optional

from ..errors import ApiError

CHUNK_SIZE = 64 * 1024

# File signatures ("magic bytes"). The file name and the client's content type are never trusted.
SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def detect_content_type(head: bytes) -> Optional[str]:
    for signature, content_type in SIGNATURES:
        if head.startswith(signature):
            return content_type
    return None


def read_limited(fileobj: BinaryIO, max_bytes: int) -> bytes:
    """Read the upload in chunks and stop as soon as it exceeds the limit."""
    buf = bytearray()
    while True:
        chunk = fileobj.read(CHUNK_SIZE)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise ApiError(
                413,
                "payload_too_large",
                f"File is larger than the {max_bytes // (1024 * 1024)} MB limit",
            )
    return bytes(buf)


def validate_image_bytes(data: bytes) -> str:
    """Returns the detected content type, or raises a clear error."""
    if not data:
        raise ApiError(400, "empty_file", "The uploaded file is empty")
    content_type = detect_content_type(data[:16])
    if content_type is None:
        raise ApiError(
            415,
            "unsupported_media_type",
            "Only JPEG and PNG images are accepted (checked by file signature, not by file name)",
        )
    return content_type


def validate_idempotency_key(key: Optional[str]) -> Optional[str]:
    if key is None:
        return None
    if not IDEMPOTENCY_KEY_PATTERN.match(key):
        raise ApiError(
            422,
            "validation_error",
            "Idempotency-Key must be 1 to 128 characters: letters, digits, dot, underscore, colon or hyphen",
        )
    return key


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()