from __future__ import annotations

from enum import Enum, auto
import logging
from pathlib import Path
from queue import Empty, SimpleQueue
import threading
import time

from capture_camera import CaptureCamera
from config import AppConfig
from display import PictureDisplay
from hardware import ControlEvent, LedStripController
from led_cues import (
    CuePlayer,
    photo_capture_cues,
    video_end_cues,
    video_start_cues,
)


LOGGER = logging.getLogger(__name__)


class CapturePhase(Enum):
    IDLE = auto()
    PHOTO_COUNTDOWN = auto()
    PHOTO_CAPTURE = auto()
    VIDEO_COUNTDOWN = auto()
    VIDEO_RECORDING = auto()
    VIDEO_END_CUES = auto()
    VIDEO_PLAYBACK = auto()


class CapturePressRole(Enum):
    NONE = auto()
    CAPTURE_CANDIDATE = auto()
    INITIAL_VIDEO_HOLD = auto()
    STOP_VIDEO = auto()


class PictureApp:
    def __init__(
        self,
        config: AppConfig,
        camera: CaptureCamera,
        display: PictureDisplay,
        led: LedStripController,
        control_events: SimpleQueue[ControlEvent],
        stop_event: threading.Event,
        playback_interrupt: threading.Event,
    ) -> None:
        self._config = config
        self._camera = camera
        self._display = display
        self._led = led
        self._control_events = control_events
        self._stop_event = stop_event
        self._playback_interrupt = playback_interrupt
        self._phase = CapturePhase.IDLE
        self._cue_player: CuePlayer | None = None
        self._video_started_at: float | None = None
        self._pending_video_path: Path | None = None
        self._current_media: Path | None = None
        self._last_preview_frame = None
        self._capture_press_role = CapturePressRole.NONE
        self._stop_video_when_started = False
        self._idle_frame_drawn = False

    def run(self) -> None:
        latest_photo = self._camera.latest_photo(self._config.storage.media_dir)
        latest_media = self._camera.latest_media(self._config.storage)
        self._current_media = latest_media
        if latest_photo is not None:
            try:
                self._display.load_still(latest_photo)
            except Exception:
                LOGGER.exception("Could not load the latest photo: %s", latest_photo)

        self._led.request(False)
        self._pause_camera_while_idle()
        self._drain_control_events()
        if (
            self._phase is CapturePhase.IDLE
            and latest_media is not None
            and latest_media.suffix.lower() == ".mp4"
        ):
            self._play_video(latest_media)

        while not self._stop_event.is_set():
            if self._display.poll_exit_requested():
                self._stop_event.set()
                break

            self._drain_control_events()
            now = time.monotonic()
            self._advance_active_capture(now)
            self._render(now)
            self._display.limit_frame_rate(self._config.display_frame_rate)

    def _drain_control_events(self, *, ignore_capture: bool = False) -> None:
        while True:
            try:
                event = self._control_events.get_nowait()
            except Empty:
                return

            if event is ControlEvent.LED_TOGGLE_PRESSED:
                self._led.toggle_strip()
            elif not ignore_capture:
                if event is ControlEvent.CAPTURE_PRESSED:
                    self._handle_capture_pressed()
                elif event is ControlEvent.CAPTURE_HELD:
                    self._handle_capture_held()
                elif event is ControlEvent.CAPTURE_RELEASED:
                    self._handle_capture_released()

    def _handle_capture_pressed(self) -> None:
        if self._phase is CapturePhase.IDLE:
            self._capture_press_role = CapturePressRole.CAPTURE_CANDIDATE
            return

        if self._phase in {
            CapturePhase.VIDEO_COUNTDOWN,
            CapturePhase.VIDEO_RECORDING,
        }:
            if self._capture_press_role is not CapturePressRole.INITIAL_VIDEO_HOLD:
                self._capture_press_role = CapturePressRole.STOP_VIDEO
            return

        self._capture_press_role = CapturePressRole.NONE
        LOGGER.debug("Ignoring capture press while phase=%s", self._phase.name)

    def _handle_capture_held(self) -> None:
        if (
            self._phase is not CapturePhase.IDLE
            or self._capture_press_role is not CapturePressRole.CAPTURE_CANDIDATE
        ):
            return

        if not self._capture_is_allowed():
            self._capture_press_role = CapturePressRole.NONE
            return

        self._capture_press_role = CapturePressRole.INITIAL_VIDEO_HOLD
        self._stop_video_when_started = False
        self._phase = CapturePhase.VIDEO_COUNTDOWN
        self._start_cues(CuePlayer(video_start_cues()), time.monotonic())
        self._resume_camera_for_capture()
        self._idle_frame_drawn = False

    def _handle_capture_released(self) -> None:
        press_role = self._capture_press_role
        self._capture_press_role = CapturePressRole.NONE

        if (
            press_role is CapturePressRole.CAPTURE_CANDIDATE
            and self._phase is CapturePhase.IDLE
        ):
            if not self._capture_is_allowed():
                return
            self._last_preview_frame = None
            self._phase = CapturePhase.PHOTO_COUNTDOWN
            self._start_cues(CuePlayer(photo_capture_cues()), time.monotonic())
            self._resume_camera_for_capture()
            self._idle_frame_drawn = False
            return

        if press_role is CapturePressRole.INITIAL_VIDEO_HOLD:
            return

        if press_role is CapturePressRole.STOP_VIDEO:
            if self._phase is CapturePhase.VIDEO_RECORDING:
                self._stop_video(automatic=False)
            elif self._phase is CapturePhase.VIDEO_COUNTDOWN:
                self._stop_video_when_started = True

    def _capture_is_allowed(self) -> bool:
        media_size = self._camera.media_size_bytes(self._config.storage)
        if media_size >= self._config.storage.max_bytes:
            self._show_storage_full(media_size)
            return False
        return True

    def _start_cues(self, cue_player: CuePlayer, now: float) -> None:
        self._cue_player = cue_player
        self._led.request(cue_player.start(now))

    def _advance_active_capture(self, now: float) -> None:
        if self._phase in {
            CapturePhase.PHOTO_COUNTDOWN,
            CapturePhase.VIDEO_COUNTDOWN,
            CapturePhase.VIDEO_END_CUES,
        }:
            self._advance_cues(now)
            return

        if self._phase is CapturePhase.VIDEO_RECORDING:
            assert self._video_started_at is not None
            if (
                now - self._video_started_at
                >= self._config.camera.video_max_seconds
            ):
                self._stop_video(automatic=True)

    def _advance_cues(self, now: float) -> None:
        assert self._cue_player is not None
        changed_state, finished = self._cue_player.update(now)
        if changed_state is not None:
            self._led.request(changed_state)
        if not finished:
            return

        self._cue_player = None
        if self._phase is CapturePhase.PHOTO_COUNTDOWN:
            self._led.request(True)
            self._capture_photo()
        elif self._phase is CapturePhase.VIDEO_COUNTDOWN:
            self._led.request(True)
            self._start_video()
        elif self._phase is CapturePhase.VIDEO_END_CUES:
            self._led.request(False)
            video_path = self._pending_video_path
            self._pending_video_path = None
            if video_path is None:
                self._return_to_idle()
            else:
                self._play_video(video_path)

    def _capture_photo(self) -> None:
        self._phase = CapturePhase.PHOTO_CAPTURE
        try:
            frame = self._last_preview_frame
            if frame is None:
                frame = self._camera.capture_preview_frame().copy()
                self._display.show_preview(frame)

            photo_path = self._camera.capture_photo(frame)
            self._display.set_still_frame(frame)
            self._current_media = photo_path
            LOGGER.info("Photo captured: %s", photo_path)
        except Exception:
            LOGGER.exception("Photo capture failed")
        finally:
            self._phase = CapturePhase.IDLE
            self._led.request(False)
            self._pause_camera_while_idle()
            self._idle_frame_drawn = False
            self._drain_control_events(ignore_capture=True)

    def _start_video(self) -> None:
        try:
            video_path = self._camera.start_video()
        except Exception:
            LOGGER.exception("Video recording could not start")
            self._stop_video_when_started = False
            self._return_to_idle()
            return

        self._video_started_at = time.monotonic()
        self._phase = CapturePhase.VIDEO_RECORDING
        self._led.request(True)
        LOGGER.info("Video recording started: %s", video_path)
        if self._stop_video_when_started:
            self._stop_video_when_started = False
            self._stop_video(automatic=False)

    def _stop_video(self, *, automatic: bool) -> None:
        self._stop_video_when_started = False
        video_path: Path | None = None
        try:
            video_path = self._camera.stop_video()
            if video_path is not None:
                self._current_media = video_path
                LOGGER.info("Video recording saved: %s", video_path)
        except Exception:
            LOGGER.exception("Video recording did not stop cleanly")

        self._video_started_at = None
        if video_path is None:
            self._return_to_idle()
            return

        if automatic:
            self._pending_video_path = video_path
            self._phase = CapturePhase.VIDEO_END_CUES
            self._start_cues(CuePlayer(video_end_cues()), time.monotonic())
            return

        self._play_video(video_path)

    def _play_video(self, video_path: Path) -> None:
        self._current_media = video_path

        while not self._stop_event.is_set():
            self._phase = CapturePhase.VIDEO_PLAYBACK
            self._led.request(False)
            self._playback_interrupt.clear()
            playback_failed = False
            try:
                self._camera.pause_for_playback()
                exit_requested = self._display.play_video_loop(
                    video_path,
                    self._stop_event,
                    self._playback_interrupt,
                )
                if exit_requested:
                    self._stop_event.set()
            except Exception:
                playback_failed = True
                LOGGER.exception("Could not play the saved video: %s", video_path)

            if self._stop_event.is_set():
                break

            if self._playback_interrupt.is_set():
                self._return_to_idle(discard_capture=False)
                self._drain_control_events()
                if (
                    not self._stop_event.is_set()
                    and self._phase is CapturePhase.IDLE
                    and self._current_media == video_path
                ):
                    continue
                self._resume_camera_for_capture()
                return

            if playback_failed:
                break

        self._return_to_idle()

    def _resume_camera_for_capture(self) -> None:
        try:
            self._camera.resume_after_playback()
        except Exception:
            LOGGER.exception("Could not start the camera for capture")
            self._stop_event.set()

    def _pause_camera_while_idle(self) -> None:
        try:
            self._camera.pause_for_playback()
        except Exception:
            LOGGER.exception("Could not stop the camera while displaying saved media")
            self._stop_event.set()

    def _show_storage_full(self, media_size: int) -> None:
        LOGGER.warning(
            "Capture blocked: media usage is %.2f GB and the limit is %.2f GB",
            media_size / 1_000_000_000,
            self._config.storage.max_bytes / 1_000_000_000,
        )
        exit_requested = self._display.show_timed_message(
            "Storage full",
            "Delete saved photos or videos to capture again",
            self._config.storage.full_message_seconds,
            self._stop_event,
        )
        if exit_requested:
            self._stop_event.set()
        self._idle_frame_drawn = False
        self._drain_control_events(ignore_capture=True)

    def _return_to_idle(self, *, discard_capture: bool = True) -> None:
        self._pending_video_path = None
        self._phase = CapturePhase.IDLE
        self._led.request(False)
        self._pause_camera_while_idle()
        self._idle_frame_drawn = False
        if discard_capture:
            self._drain_control_events(ignore_capture=True)

    def _render(self, now: float) -> None:
        if self._phase is CapturePhase.IDLE:
            if not self._idle_frame_drawn:
                self._display.show_still()
                self._idle_frame_drawn = True
            return
        if self._phase is CapturePhase.VIDEO_PLAYBACK:
            return

        frame = self._camera.capture_preview_frame()
        self._last_preview_frame = frame.copy()
        recording_dot_visible = False
        if (
            self._phase is CapturePhase.VIDEO_RECORDING
            and self._video_started_at is not None
        ):
            elapsed = max(0.0, now - self._video_started_at)
            recording_dot_visible = elapsed % 1.0 < 0.5
        self._display.show_preview(frame, recording_dot_visible)
