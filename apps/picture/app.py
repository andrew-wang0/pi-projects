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
from hardware import ControlEvent, LedStripController, PhysicalControls
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


class PictureApp:
    def __init__(
        self,
        config: AppConfig,
        camera: CaptureCamera,
        display: PictureDisplay,
        led: LedStripController,
        controls: PhysicalControls,
        control_events: SimpleQueue[ControlEvent],
        stop_event: threading.Event,
    ) -> None:
        self._config = config
        self._camera = camera
        self._display = display
        self._led = led
        self._controls = controls
        self._control_events = control_events
        self._stop_event = stop_event
        self._phase = CapturePhase.IDLE
        self._cue_player: CuePlayer | None = None
        self._video_started_at: float | None = None
        self._pending_video_path: Path | None = None
        self._idle_frame_drawn = False

    def run(self) -> None:
        latest_photo = self._camera.latest_photo(self._config.storage.photos_dir)
        if latest_photo is not None:
            try:
                self._display.load_still(latest_photo)
            except Exception:
                LOGGER.exception("Could not load the latest photo: %s", latest_photo)

        self._led.request(True)

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
            elif event is ControlEvent.CAPTURE_PRESSED and not ignore_capture:
                self._handle_capture_pressed()

    def _handle_capture_pressed(self) -> None:
        if self._phase is CapturePhase.VIDEO_RECORDING:
            self._stop_video(automatic=False)
            return

        if self._phase is not CapturePhase.IDLE:
            LOGGER.debug("Ignoring capture press while phase=%s", self._phase.name)
            return

        now = time.monotonic()
        if self._controls.video_mode_selected:
            self._phase = CapturePhase.VIDEO_COUNTDOWN
            self._start_cues(CuePlayer(video_start_cues()), now)
        else:
            self._phase = CapturePhase.PHOTO_COUNTDOWN
            self._start_cues(CuePlayer(photo_capture_cues()), now)

        self._idle_frame_drawn = False

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
        self._led.request(True)
        if self._phase is CapturePhase.PHOTO_COUNTDOWN:
            self._capture_photo()
        elif self._phase is CapturePhase.VIDEO_COUNTDOWN:
            self._start_video()
        elif self._phase is CapturePhase.VIDEO_END_CUES:
            video_path = self._pending_video_path
            self._pending_video_path = None
            if video_path is None:
                self._return_to_idle()
            else:
                self._play_video(video_path)

    def _capture_photo(self) -> None:
        self._phase = CapturePhase.PHOTO_CAPTURE
        try:
            photo_path = self._camera.capture_photo()
            self._display.load_still(photo_path)
            LOGGER.info("Photo captured: %s", photo_path)
        except Exception:
            LOGGER.exception("Photo capture failed")
        finally:
            self._phase = CapturePhase.IDLE
            self._led.request(True)
            self._idle_frame_drawn = False
            self._drain_control_events(ignore_capture=True)

    def _start_video(self) -> None:
        try:
            video_path = self._camera.start_video()
        except Exception:
            LOGGER.exception("Video recording could not start")
            self._phase = CapturePhase.IDLE
            self._led.request(True)
            self._idle_frame_drawn = False
            self._drain_control_events(ignore_capture=True)
            return

        self._video_started_at = time.monotonic()
        self._phase = CapturePhase.VIDEO_RECORDING
        self._led.request(True)
        LOGGER.info("Video recording started: %s", video_path)

    def _stop_video(self, *, automatic: bool) -> None:
        video_path: Path | None = None
        try:
            video_path = self._camera.stop_video()
            if video_path is not None:
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
        self._phase = CapturePhase.VIDEO_PLAYBACK
        self._led.request(True)
        camera_paused = False
        try:
            self._camera.pause_for_playback()
            camera_paused = True
            exit_requested = self._display.play_video(video_path, self._stop_event)
            if exit_requested:
                self._stop_event.set()
        except Exception:
            LOGGER.exception("Could not play the saved video: %s", video_path)
        finally:
            if camera_paused and not self._stop_event.is_set():
                try:
                    self._camera.resume_after_playback()
                except Exception:
                    LOGGER.exception("Could not restart the camera after video playback")
                    self._stop_event.set()
            self._return_to_idle()

    def _return_to_idle(self) -> None:
        self._pending_video_path = None
        self._phase = CapturePhase.IDLE
        self._led.request(True)
        self._idle_frame_drawn = False
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
        recording_dot_visible = (
            self._phase is CapturePhase.VIDEO_RECORDING
            and self._video_started_at is not None
            and int((now - self._video_started_at) * 2) % 2 == 0
        )
        self._display.show_preview(frame, recording_dot_visible)
