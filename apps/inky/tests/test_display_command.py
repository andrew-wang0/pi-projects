from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from display_command import DisplayCommandError, parse_display_request


def command(**overrides) -> bytes:
    payload = {
        "version": 1,
        "request_id": "request-123",
        "content_type": "image/jpeg",
        "data": base64.b64encode(b"image bytes").decode(),
        **overrides,
    }
    return json.dumps(payload).encode()


class ParseDisplayRequestTests(unittest.TestCase):
    def test_parses_supported_image(self) -> None:
        request = parse_display_request(command(), max_image_bytes=1_024)

        self.assertEqual(request.request_id, "request-123")
        self.assertEqual(request.content_type, "image/jpeg")
        self.assertEqual(request.image, b"image bytes")

    def test_rejects_unknown_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "version"):
            parse_display_request(command(version=2), max_image_bytes=1_024)

    def test_rejects_unsupported_content_type(self) -> None:
        with self.assertRaisesRegex(DisplayCommandError, "content type") as raised:
            parse_display_request(
                command(content_type="image/svg+xml"),
                max_image_bytes=1_024,
            )

        self.assertEqual(raised.exception.request_id, "request-123")

    def test_rejects_non_string_content_type(self) -> None:
        with self.assertRaisesRegex(DisplayCommandError, "content type"):
            parse_display_request(
                command(content_type=["image/jpeg"]),
                max_image_bytes=1_024,
            )

    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(ValueError, "base64"):
            parse_display_request(command(data="not base64"), max_image_bytes=1_024)

    def test_rejects_decoded_image_over_limit(self) -> None:
        encoded = base64.b64encode(b"x" * 1_025).decode()

        with self.assertRaisesRegex(ValueError, "too large"):
            parse_display_request(command(data=encoded), max_image_bytes=1_024)

    def test_correlates_oversized_command_from_prefix(self) -> None:
        oversized = command(data="x" * 6_000)

        with self.assertRaisesRegex(DisplayCommandError, "too large") as raised:
            parse_display_request(oversized, max_image_bytes=1_024)

        self.assertEqual(raised.exception.request_id, "request-123")

    def test_rejects_empty_request_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "request_id"):
            parse_display_request(command(request_id=" "), max_image_bytes=1_024)


if __name__ == "__main__":
    unittest.main()
