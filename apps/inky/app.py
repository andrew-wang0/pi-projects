from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import logging
from pathlib import Path
from queue import Empty, Queue, SimpleQueue
import threading
import time

from PIL import Image

from camera import Camera
from display import InkyDisplay
from hardware import ButtonEvent, CaptureButton, ShowLight, SignalLed


LOGGER = logging.getLogger(__name__)


class InkyApp:
    def __init__(
        self,
        camera: Camera,
        display: InkyDisplay,
        controls: CaptureButton,
        signal_led: SignalLed,
        show_light: ShowLight,
        events: SimpleQueue[ButtonEvent],
        display_requests: Queue[DisplayRequest],
        stop_event: threading.Event,
        image_dir: Path,
        on_photo: Callable[[Path], None],
        on_display_status: Callable[[str, str | None, str | None], None],
    ) -> None:
        self._camera = camera
        self._display = display
        self._controls = controls
        self._signal_led = signal_led
        self._show_light = show_light
        self._events = events
        self._display_requests = display_requests
        self._stop_event = stop_event
        self._image_dir = image_dir
        self._on_photo = on_photo
        self._on_display_status = on_display_status
        self._capture_prepared = False

    def run(self) -> None:
        while not self._stop_event.is_set():
            if not self._capture_prepared:
                try:
                    request = self._display_requests.get_nowait()
                except Empty:
                    pass
                else:
                    self._show_remote(request)
                    continue

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
            self._capture_prepared = True
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

            self._show_light.start_busy()
            try:
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
            finally:
                self._show_light.stop_busy()
        except Exception:
            LOGGER.exception("Inky image preparation or display update failed")
        finally:
            self._capture_prepared = False
            self._discard_events()
            self._controls.set_enabled(True)

    def _show_remote(self, request: DisplayRequest) -> None:
        self._controls.set_enabled(False)
        self._report_display_status("updating", request.request_id)
        staged: Path | None = None
        try:
            with Image.open(BytesIO(request.image)) as uploaded:
                actual_content_type = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "WEBP": "image/webp",
                }.get(uploaded.format)
                if actual_content_type != request.content_type:
                    raise ValueError("image content does not match its content type")
                width, height = uploaded.size
                if width > 4_096 or height > 4_096 or width * height > 16_000_000:
                    raise ValueError("uploaded image dimensions are too large")
                uploaded.load()
                prepared = self._display.prepare(uploaded)
            staged = self._stage(prepared)
            self._display.show(prepared)
            path = self._commit_staged(staged)
            staged = None
            try:
                self._on_photo(path)
            except Exception:
                LOGGER.exception("Home Assistant photo publication failed")
        except Exception as error:
            LOGGER.exception("Remote image display update failed")
            self._report_display_status("error", request.request_id, str(error))
        else:
            self._report_display_status("idle", request.request_id)
        finally:
            if staged is not None:
                try:
                    staged.unlink(missing_ok=True)
                except OSError:
                    LOGGER.warning("Could not remove failed staged image %s", staged)
            self._discard_events()
            self._controls.set_enabled(True)

    def _report_display_status(
        self,
        state: str,
        request_id: str,
        message: str | None = None,
    ) -> None:
        try:
            self._on_display_status(state, request_id, message)
        except Exception:
            LOGGER.exception("Home Assistant status publication failed")

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

    def _stage(self, image: Image.Image) -> Path:
        path = self._image_dir / f".display-{time.time_ns()}.pending"
        image.save(path, format="PNG")
        return path

    def _commit_staged(self, staged: Path) -> Path:
        path = self._image_dir / f"{int(time.time())}.png"
        staged.replace(path)
        LOGGER.info("Stored %s", path)
        return path
