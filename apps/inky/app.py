from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path
from queue import Empty, SimpleQueue
import threading
import time

from PIL import Image

from camera import Camera
from display import InkyDisplay
from hardware import ButtonEvent, CaptureButton, SignalLed


LOGGER = logging.getLogger(__name__)


class InkyApp:
    def __init__(
        self,
        camera: Camera,
        display: InkyDisplay,
        controls: CaptureButton,
        signal_led: SignalLed,
        events: SimpleQueue[ButtonEvent],
        stop_event: threading.Event,
        image_dir: Path,
        on_photo: Callable[[Path], None],
    ) -> None:
        self._camera = camera
        self._display = display
        self._controls = controls
        self._signal_led = signal_led
        self._events = events
        self._stop_event = stop_event
        self._image_dir = image_dir
        self._on_photo = on_photo

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._events.get(timeout=0.1)
            except Empty:
                continue

            if event is ButtonEvent.PRESSED:
                self._prepare_capture()
            elif event is ButtonEvent.RELEASED:
                self._capture_and_show()

    def _prepare_capture(self) -> None:
        self._signal_led.on()
        try:
            self._camera.start()
        except Exception:
            LOGGER.exception("Camera start failed")
            self._signal_led.off()
            self._controls.set_enabled(False)
            self._discard_events()
            self._controls.set_enabled(True)

    def _capture_and_show(self) -> None:
        self._controls.set_enabled(False)
        try:
            try:
                image = self._camera.capture()
            except Exception:
                LOGGER.exception("Photo capture failed")
                return
            finally:
                self._signal_led.off()
                try:
                    self._camera.stop()
                except Exception:
                    LOGGER.exception("Camera stop failed")

            prepared = self._display.prepare(image)
            try:
                path = self._store(prepared)
            except Exception:
                LOGGER.exception("Image storage failed")
            else:
                try:
                    self._on_photo(path)
                except Exception:
                    LOGGER.exception("Home Assistant photo publication failed")
            self._display.show(prepared)
        except Exception:
            LOGGER.exception("Inky image preparation or display update failed")
        finally:
            self._discard_events()
            self._controls.set_enabled(True)

    def _discard_events(self) -> None:
        while True:
            try:
                self._events.get_nowait()
            except Empty:
                return

    def _store(self, image: Image.Image) -> Path:
        path = self._image_dir / f"{int(time.time())}.png"
        image.save(path, format="PNG")
        LOGGER.info("Stored %s", path)
        return path
