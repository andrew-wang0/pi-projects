from __future__ import annotations

from libcamera import Transform, controls
from PIL import Image
from picamera2 import Picamera2

from config import Config


class Camera:
    def __init__(self, config: Config) -> None:
        self._camera = Picamera2()
        self._running = False
        self._camera.configure(
            self._camera.create_still_configuration(
                main={"size": config.camera_size, "format": "RGB888"},
                transform=Transform(
                    hflip=config.camera_hflip,
                    vflip=config.camera_vflip,
                ),
                controls={"AfMode": controls.AfModeEnum.Continuous},
                buffer_count=3,
            )
        )

    def start(self) -> None:
        self._camera.start()
        self._running = True

    def capture(self) -> Image.Image:
        with self._camera.captured_request(flush=True) as request:
            frame = request.make_array("main")

        # Picamera2's RGB888 stream is BGR byte order in a NumPy array.
        return Image.fromarray(frame[:, :, ::-1].copy())

    def stop(self) -> None:
        if self._running:
            self._camera.stop()
            self._running = False

    def close(self) -> None:
        self.stop()
        self._camera.close()
