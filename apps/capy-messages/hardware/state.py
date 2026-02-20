import threading


class RuntimeState:
    def __init__(self, initial_background_id: str) -> None:
        self.display_active = threading.Event()
        self.shutdown = threading.Event()

        self._lock = threading.Lock()
        self._background_id = initial_background_id

    def set_background_id(self, background_id: str) -> None:
        with self._lock:
            self._background_id = background_id

    def get_background_id(self) -> str:
        with self._lock:
            return self._background_id
