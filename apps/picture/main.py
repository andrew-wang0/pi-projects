#!/usr/bin/env python3
from __future__ import annotations

import logging
from queue import SimpleQueue
import signal
import threading

from app import PictureApp
from capture_camera import CaptureCamera
from config import load_config
from display import PictureDisplay
from hardware import ControlEvent, LedStripController, PhysicalControls, use_lgpio


LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    config.storage.photos_dir.mkdir(parents=True, exist_ok=True)
    config.storage.videos_dir.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()
    playback_interrupt = threading.Event()
    control_events: SimpleQueue[ControlEvent] = SimpleQueue()

    def request_stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    display: PictureDisplay | None = None
    led: LedStripController | None = None
    controls: PhysicalControls | None = None
    camera: CaptureCamera | None = None

    try:
        use_lgpio()
        display = PictureDisplay()
        led = LedStripController(config.pins)

        def on_control_event(event: ControlEvent) -> None:
            if event is ControlEvent.LED_TOGGLE_PRESSED:
                assert led is not None
                led.toggle_strip()
            else:
                playback_interrupt.set()
                control_events.put(event)

        controls = PhysicalControls(config.pins, on_control_event)
        camera = CaptureCamera(config.camera, config.storage)

        PictureApp(
            config=config,
            camera=camera,
            display=display,
            led=led,
            controls=controls,
            control_events=control_events,
            stop_event=stop_event,
            playback_interrupt=playback_interrupt,
        ).run()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        for name, resource in (
            ("controls", controls),
            ("camera", camera),
            ("LED", led),
            ("display", display),
        ):
            if resource is None:
                continue
            try:
                resource.close()
            except Exception:
                LOGGER.exception("Could not close %s cleanly", name)

    LOGGER.info("Picture app stopped")


if __name__ == "__main__":
    main()
