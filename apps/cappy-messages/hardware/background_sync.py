import json
import threading
import time
from typing import Callable, Iterable

import requests

from config import MESSAGE_API


class BackgroundSyncClient:
    def __init__(self, on_background_id: Callable[[str], None], shutdown_event: threading.Event) -> None:
        self._on_background_id = on_background_id
        self._shutdown = shutdown_event

    def run_forever(self) -> None:
        session = requests.Session()
        poll_session = requests.Session()

        try:
            while not self._shutdown.is_set():
                try:
                    self._fetch_background_state(session)
                except Exception as exc:
                    print(f"Background state fetch failed: {exc}")

                if self._shutdown.is_set():
                    break

                periodic_refresh_shutdown = threading.Event()
                periodic_refresh_thread = threading.Thread(
                    target=self._refresh_state_periodically,
                    args=(poll_session, periodic_refresh_shutdown),
                    daemon=True,
                )
                periodic_refresh_thread.start()

                try:
                    with session.get(
                        MESSAGE_API.stream_url,
                        stream=True,
                        timeout=(MESSAGE_API.connect_timeout_seconds, MESSAGE_API.read_timeout_seconds),
                        headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
                    ) as response:
                        response.raise_for_status()

                        for raw_event in self._iter_sse_data(response):
                            try:
                                payload = json.loads(raw_event)
                            except json.JSONDecodeError:
                                continue

                            background_id = self._extract_background_id(payload)
                            if background_id:
                                self._on_background_id(background_id)

                            if self._shutdown.is_set():
                                break

                except Exception as exc:
                    if not self._shutdown.is_set():
                        print(f"Background stream disconnected, reconnecting: {exc}")
                        self._sleep_until_retry(MESSAGE_API.reconnect_delay_seconds)
                finally:
                    periodic_refresh_shutdown.set()
                    periodic_refresh_thread.join(timeout=1.0)
        finally:
            session.close()
            poll_session.close()

    def _fetch_background_state(self, session: requests.Session) -> None:
        response = session.get(
            MESSAGE_API.state_url,
            timeout=(MESSAGE_API.connect_timeout_seconds, MESSAGE_API.read_timeout_seconds),
            headers={"Cache-Control": "no-store"},
        )
        response.raise_for_status()

        background_id = self._extract_background_id(response.json())
        if background_id:
            self._on_background_id(background_id)

    @staticmethod
    def _extract_background_id(payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        background_id = payload.get("activeBackgroundId")
        if isinstance(background_id, str) and background_id:
            return background_id
        return None

    def _iter_sse_data(self, response: requests.Response) -> Iterable[str]:
        data_lines: list[str] = []

        for raw_line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if self._shutdown.is_set():
                return
            if raw_line is None:
                continue

            line = raw_line.strip("\r")

            if line == "":
                if data_lines:
                    yield "\n".join(data_lines)
                    data_lines.clear()
                continue

            if line.startswith(":"):
                continue

            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())

        if data_lines:
            yield "\n".join(data_lines)

    def _refresh_state_periodically(
        self,
        session: requests.Session,
        stop_event: threading.Event,
    ) -> None:
        while not self._shutdown.is_set():
            if stop_event.wait(MESSAGE_API.state_refresh_seconds):
                return
            if self._shutdown.is_set():
                return

            try:
                self._fetch_background_state(session)
            except Exception as exc:
                if not self._shutdown.is_set():
                    print(f"Background periodic state refresh failed: {exc}")

    def _sleep_until_retry(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._shutdown.is_set():
                return
            time.sleep(0.05)
