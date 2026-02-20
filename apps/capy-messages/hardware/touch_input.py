import threading
import time
from typing import Callable

from config import TOUCH


class TouchWatcher:
    def __init__(self, on_touch: Callable[[], None], shutdown_event: threading.Event) -> None:
        self._on_touch = on_touch
        self._shutdown = shutdown_event
        self._last_touch_at = 0.0

    def run_forever(self) -> None:
        if not TOUCH.enabled:
            return

        try:
            from evdev import InputDevice, ecodes, list_devices
        except ImportError:
            print("Touch watcher disabled: install 'evdev' to enable touch wake/reset.")
            return

        devices: dict[str, InputDevice] = {}
        next_rescan_at = 0.0

        try:
            while not self._shutdown.is_set():
                now = time.monotonic()

                if now >= next_rescan_at:
                    self._refresh_devices(devices, InputDevice, list_devices, ecodes)
                    next_rescan_at = now + max(0.25, TOUCH.rescan_seconds)

                for path, device in list(devices.items()):
                    try:
                        event = device.read_one()
                        while event is not None:
                            if self._is_touch_event(event, ecodes):
                                self._emit_touch_if_due()
                            event = device.read_one()
                    except OSError:
                        self._close_device(path, devices)

                time.sleep(0.01)
        finally:
            for path in list(devices):
                self._close_device(path, devices)

    def _emit_touch_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_touch_at < max(0.01, TOUCH.debounce_seconds):
            return

        self._last_touch_at = now
        self._on_touch()

    def _refresh_devices(self, devices, InputDevice, list_devices, ecodes) -> None:
        discovered_paths = set(list_devices())

        for stale_path in [path for path in devices if path not in discovered_paths]:
            self._close_device(stale_path, devices)

        for path in discovered_paths:
            if path in devices:
                continue

            try:
                device = InputDevice(path)
            except Exception:
                continue

            if TOUCH.device_name_hint and TOUCH.device_name_hint.lower() not in device.name.lower():
                device.close()
                continue

            if not self._supports_touch(device, ecodes):
                device.close()
                continue

            devices[path] = device

    @staticmethod
    def _supports_touch(device, ecodes) -> bool:
        try:
            caps = device.capabilities()
        except Exception:
            return False

        key_caps = set(caps.get(ecodes.EV_KEY, []))
        abs_caps = set(caps.get(ecodes.EV_ABS, []))

        has_touch_key = any(
            code in key_caps
            for code in (
                ecodes.BTN_TOUCH,
                ecodes.BTN_TOOL_FINGER,
                ecodes.BTN_LEFT,
            )
        )
        has_touch_abs = any(
            code in abs_caps
            for code in (
                ecodes.ABS_MT_TRACKING_ID,
                ecodes.ABS_MT_POSITION_X,
                ecodes.ABS_X,
                ecodes.ABS_Y,
            )
        )

        return has_touch_key or has_touch_abs

    @staticmethod
    def _is_touch_event(event, ecodes) -> bool:
        if event.type == ecodes.EV_KEY:
            if event.code in (ecodes.BTN_TOUCH, ecodes.BTN_TOOL_FINGER, ecodes.BTN_LEFT):
                return event.value == 1
            return False

        if event.type == ecodes.EV_ABS and event.code == ecodes.ABS_MT_TRACKING_ID:
            # Non-negative tracking id indicates a new touch contact.
            return event.value >= 0

        return False

    @staticmethod
    def _close_device(path: str, devices) -> None:
        device = devices.pop(path, None)
        if device is None:
            return

        try:
            device.close()
        except Exception:
            return
