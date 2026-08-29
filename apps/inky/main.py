#!/usr/bin/env python3
from __future__ import annotations

import logging
from queue import Empty, Full, Queue, SimpleQueue
import signal
import threading

from app import InkyApp
from camera import Camera
from config import load_config
from display import InkyDisplay
from display_command import DisplayRequest
from hardware import ButtonEvent, CaptureButton, ShowLight, SignalLed, use_lgpio
from home_assistant import HomeAssistant


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
    display_requests: Queue[DisplayRequest] = Queue(maxsize=1)

    def enqueue_display(request: DisplayRequest) -> None:
        try:
            display_requests.put_nowait(request)
            return
        except Full:
            pass
        try:
            display_requests.get_nowait()
        except Empty:
            pass
        display_requests.put_nowait(request)

    def stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    controls = None
    camera = None
    show_light = None
    signal_led = None
    home_assistant = None
    try:
        use_lgpio()
        display = InkyDisplay(config)
        show_light = ShowLight(config)
        signal_led = SignalLed(config)
        controls = CaptureButton(config, events.put)
        camera = Camera(config)
        home_assistant = HomeAssistant(config, show_light, enqueue_display)
        home_assistant.start()
        InkyApp(
            camera,
            display,
            controls,
            signal_led,
            events,
            display_requests,
            stop_event,
            config.image_dir,
            home_assistant.publish_photo,
            home_assistant.publish_display_status,
        ).run()
    finally:
        for resource in (
            controls,
            camera,
            signal_led,
            home_assistant,
            show_light,
        ):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    LOGGER.exception("Could not close %s", type(resource).__name__)


if __name__ == "__main__":
    main()
