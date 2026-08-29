from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import json


SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class DisplayRequest:
    request_id: str
    content_type: str
    image: bytes


def parse_display_request(payload: bytes, max_image_bytes: int) -> DisplayRequest:
    if len(payload) > (max_image_bytes * 4 // 3) + 4_096:
        raise ValueError("command payload is too large")

    try:
        command = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("command must be valid JSON") from error

    if not isinstance(command, dict):
        raise ValueError("command must be a JSON object")
    if command.get("version") != 1:
        raise ValueError("unsupported command version")

    request_id = command.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id must be a non-empty string")
    if len(request_id) > 128:
        raise ValueError("request_id is too long")

    content_type = command.get("content_type")
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError("unsupported image content type")

    encoded = command.get("data")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("data must be a base64 string")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("data must be valid base64") from error
    if not image:
        raise ValueError("image cannot be empty")
    if len(image) > max_image_bytes:
        raise ValueError("image is too large")

    return DisplayRequest(
        request_id=request_id.strip(),
        content_type=content_type,
        image=image,
    )
