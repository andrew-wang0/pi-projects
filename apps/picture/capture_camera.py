from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from libcamera import Transform, controls
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput

from config import CameraConfig, StorageConfig


LOGGER = logging.getLogger(__name__)


class CaptureCamera:
    def __init__(self, config: CameraConfig, storage: StorageConfig) -> None:
        self._config = config
        self._storage = storage
        self._camera = Picamera2()
        self._encoder: H264Encoder | None = None
        self._video_output: PyavOutput | None = None
        self._video_path: Path | None = None
        self._started = False

        transform = Transform(
            hflip=config.horizontal_flip,
            vflip=config.vertical_flip,
        )
        camera_controls = {
            "FrameRate": config.frame_rate,
            "AfMode": controls.AfModeEnum.Continuous,
        }
        self._video_configuration = self._camera.create_video_configuration(
            main={
                "size": config.preview_size,
                "format": "RGB888",
            },
            raw={"size": config.still_size},
            transform=transform,
            controls=camera_controls,
            buffer_count=3,
            display="main",
        )
        self._still_configuration = self._camera.create_still_configuration(
            main={
                "size": config.still_size,
                "format": "RGB888",
            },
            raw={"size": config.still_size},
            transform=transform,
            controls={"AfMode": controls.AfModeEnum.Continuous},
            buffer_count=2,
            display=None,
        )

        self._camera.configure(self._video_configuration)
        self._camera.start()
        self._started = True

    @property
    def preview_size(self) -> tuple[int, int]:
        return self._config.preview_size

    @property
    def recording(self) -> bool:
        return self._encoder is not None

    def capture_preview_frame(self):
        return self._camera.capture_array("main")

    def capture_photo(self) -> Path:
        path = self._new_media_path(self._storage.photos_dir, "picture", ".jpg")
        LOGGER.info("Capturing photo to %s", path)
        self._camera.switch_mode_and_capture_file(
            self._still_configuration,
            str(path),
            name="main",
            format="jpeg",
        )
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError("The photo capture did not produce a non-empty file")
        return path

    def start_video(self) -> Path:
        if self.recording:
            raise RuntimeError("Video recording is already active")

        path = self._new_media_path(self._storage.videos_dir, "video", ".mp4")
        encoder = H264Encoder(
            bitrate=self._config.video_bitrate,
            repeat=True,
            framerate=self._config.frame_rate,
        )
        output = PyavOutput(str(path))

        LOGGER.info("Starting video recording to %s", path)
        try:
            self._camera.start_encoder(encoder, output, name="main")
        except Exception:
            try:
                output.stop()
            except Exception:
                pass
            path.unlink(missing_ok=True)
            raise

        self._encoder = encoder
        self._video_output = output
        self._video_path = path
        return path

    def stop_video(self) -> Path | None:
        if self._encoder is None:
            return None

        encoder = self._encoder
        path = self._video_path

        LOGGER.info("Stopping video recording")
        try:
            self._camera.stop_encoder(encoder)
        finally:
            self._encoder = None
            self._video_output = None
            self._video_path = None

        if path is None or not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError("The video output did not produce a non-empty file")
        return path

    def pause_for_playback(self) -> None:
        if self.recording:
            raise RuntimeError("Cannot pause the camera during video recording")
        if self._started:
            self._camera.stop()
            self._started = False

    def resume_after_playback(self) -> None:
        if not self._started:
            self._camera.start()
            self._started = True

    def close(self) -> None:
        if self.recording:
            try:
                self.stop_video()
            except Exception:
                LOGGER.exception("Could not finish the active video recording")

        if self._started:
            self._camera.stop()
            self._started = False
        self._camera.close()

    @staticmethod
    def latest_photo(photos_dir: Path) -> Path | None:
        try:
            photos = tuple(photos_dir.glob("*.jpg"))
        except OSError:
            LOGGER.exception("Could not scan the photo directory")
            return None

        if not photos:
            return None
        # Generated names use a fixed-width timestamp, so lexical order is
        # capture order even if copying files changes their filesystem mtime.
        return max(photos, key=lambda path: path.name)

    @staticmethod
    def latest_media(storage: StorageConfig) -> Path | None:
        try:
            media = (
                *storage.photos_dir.glob("picture_*.jpg"),
                *storage.videos_dir.glob("video_*.mp4"),
            )
        except OSError:
            LOGGER.exception("Could not scan the media directories")
            return None

        if not media:
            return None

        def capture_timestamp(path: Path) -> str:
            _prefix, _separator, timestamp = path.stem.partition("_")
            return timestamp

        return max(media, key=capture_timestamp)

    @staticmethod
    def media_size_bytes(storage: StorageConfig) -> int:
        total = 0
        for directory in (storage.photos_dir, storage.videos_dir):
            try:
                paths = directory.rglob("*")
                for path in paths:
                    if path.is_file() and not path.is_symlink():
                        total += path.stat().st_size
            except OSError:
                LOGGER.exception("Could not calculate media usage in %s", directory)
                # Fail closed so an unreadable directory cannot bypass the cap.
                return storage.max_bytes
        return total

    @staticmethod
    def _new_media_path(directory: Path, prefix: str, suffix: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return directory / f"{prefix}_{timestamp}{suffix}"
