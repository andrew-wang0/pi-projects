from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from queue import Empty, SimpleQueue
import threading

from PIL import Image

from camera import Camera
from display import InkyDisplay
from hardware import ButtonEvent, CaptureButton, CaptureLights


LOGGER = logging.getLogger(__name__)


class InkyApp:
    def __init__(
        self,
        camera: Camera,
        display: InkyDisplay,
        controls: CaptureButton,
        light: CaptureLights,
        events: SimpleQueue[ButtonEvent],
        stop_event: threading.Event,
        image_dir: Path,
    ) -> None:
        self._camera = camera
        self._display = display
        self._controls = controls
        self._light = light
        self._events = events
        self._stop_event = stop_event
        self._image_dir = image_dir

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
        self._light.on()
        try:
            self._camera.start()
        except Exception:
            LOGGER.exception("Camera start failed")
            self._light.off()
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
                self._light.off()
                try:
                    self._camera.stop()
                except Exception:
                    LOGGER.exception("Camera stop failed")

            prepared = self._display.prepare(image)
            try:
                self._store(prepared)
            except Exception:
                LOGGER.exception("Image storage failed")
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

    def _store(self, image: Image.Image) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self._image_dir / f"inky_{timestamp}.png"
        image.save(path, format="PNG")
        LOGGER.info("Stored %s", path)
