import threading
import time


class RuntimeState:
    def __init__(self, initial_background_id: str) -> None:
        self.display_active = threading.Event()
        self.shutdown = threading.Event()

        self._lock = threading.Lock()
        self._background_id = initial_background_id
        self._pir_flash_until = 0.0

    def set_background_id(self, background_id: str) -> None:
        with self._lock:
            self._background_id = background_id

    def get_background_id(self) -> str:
        with self._lock:
            return self._background_id

    def trigger_pir_flash(self, duration_seconds: float) -> None:
        with self._lock:
            self._pir_flash_until = time.monotonic() + duration_seconds

    def pir_flash_remaining(self, now: float) -> float:
        with self._lock:
            return self._pir_flash_until - now
