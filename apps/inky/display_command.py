from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import json
import re


SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]+")


class DisplayCommandError(ValueError):
    def __init__(self, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id


@dataclass(frozen=True)
class DisplayRequest:
    request_id: str
    content_type: str
    image: bytes


def parse_display_request(payload: bytes, max_image_bytes: int) -> DisplayRequest:
    if len(payload) > (max_image_bytes * 4 // 3) + 4_096:
        match = re.search(
            rb'"request_id"\s*:\s*"([A-Za-z0-9._:-]{1,128})"',
            payload[:4_096],
        )
        request_id = match.group(1).decode() if match is not None else None
        raise DisplayCommandError("command payload is too large", request_id)

    try:
        command = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DisplayCommandError("command must be valid JSON") from error

    if not isinstance(command, dict):
        raise DisplayCommandError("command must be a JSON object")

    request_id = command.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise DisplayCommandError("request_id must be a non-empty string")
    request_id = request_id.strip()
    if len(request_id) > 128:
        raise DisplayCommandError("request_id is too long")
    if REQUEST_ID_PATTERN.fullmatch(request_id) is None:
        raise DisplayCommandError("request_id contains unsupported characters")

    def invalid(message: str) -> DisplayCommandError:
        return DisplayCommandError(message, request_id)

    if command.get("version") != 1:
        raise invalid("unsupported command version")

    content_type = command.get("content_type")
    if not isinstance(content_type, str) or content_type not in SUPPORTED_CONTENT_TYPES:
        raise invalid("unsupported image content type")

    encoded = command.get("data")
    if not isinstance(encoded, str) or not encoded:
        raise invalid("data must be a base64 string")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise invalid("data must be valid base64") from error
    if not image:
        raise invalid("image cannot be empty")
    if len(image) > max_image_bytes:
        raise invalid("image is too large")

    return DisplayRequest(
        request_id=request_id,
        content_type=content_type,
        image=image,
    )
