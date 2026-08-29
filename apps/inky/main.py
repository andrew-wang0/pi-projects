#!/usr/bin/env python3
from __future__ import annotations

import logging
from queue import SimpleQueue
import signal
import threading

from app import InkyApp
from camera import Camera
from config import load_config
from display import InkyDisplay
from hardware import ButtonEvent, CaptureButton, CaptureLights, use_lgpio


LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    config.image_dir.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()
    events: SimpleQueue[ButtonEvent] = SimpleQueue()

    def stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    controls = None
    camera = None
    light = None
    try:
        use_lgpio()
        display = InkyDisplay(config)
        light = CaptureLights(config)
        controls = CaptureButton(config, events.put)
        camera = Camera(config)
        InkyApp(
            camera,
            display,
            controls,
            light,
            events,
            stop_event,
            config.image_dir,
        ).run()
    finally:
        for resource in (controls, camera, light):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    LOGGER.exception("Could not close %s", type(resource).__name__)


if __name__ == "__main__":
    main()
