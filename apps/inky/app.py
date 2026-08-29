from __future__ import annotations

import logging
from queue import Empty, SimpleQueue
import threading

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
    ) -> None:
        self._camera = camera
        self._display = display
        self._controls = controls
        self._light = light
        self._events = events
        self._stop_event = stop_event

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

            try:
                self._display.show(image)
            except Exception:
                LOGGER.exception("Inky display update failed")
        finally:
            self._discard_events()
            self._controls.set_enabled(True)

    def _discard_events(self) -> None:
        while True:
            try:
                self._events.get_nowait()
            except Empty:
                return
