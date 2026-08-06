from __future__ import annotations

from pathlib import Path
import threading
import time

import av
import pygame


class PictureDisplay:
    def __init__(self) -> None:
        pygame.init()
        pygame.mouse.set_visible(False)
        self._screen = pygame.display.set_mode(
            (0, 0),
            pygame.FULLSCREEN | pygame.NOFRAME,
        )
        pygame.display.set_caption("Picture")
        self._size = self._screen.get_size()
        self._clock = pygame.time.Clock()
        self._still_surface: pygame.Surface | None = None

    def poll_exit_requested(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key in {
                pygame.K_ESCAPE,
                pygame.K_q,
            }:
                return True
        return False

    def load_still(self, path: Path) -> None:
        loaded = pygame.image.load(str(path)).convert()
        self._still_surface = self._scale_to_cover(loaded, smooth=True)

    def show_still(self) -> None:
        if self._still_surface is None:
            self._show_empty_state()
        else:
            self._screen.blit(self._still_surface, (0, 0))
        pygame.display.flip()

    def show_preview(self, frame, recording_dot_visible: bool = False) -> None:
        height, width = frame.shape[:2]
        surface = pygame.image.frombuffer(frame.data, (width, height), "BGR")
        scaled = self._scale_to_cover(surface, smooth=False)
        self._screen.blit(scaled, (0, 0))

        if recording_dot_visible:
            radius = max(8, min(self._size) // 32)
            center = (
                self._size[0] - radius * 2,
                radius * 2,
            )
            pygame.draw.circle(self._screen, (110, 0, 0), center, radius + 3)
            pygame.draw.circle(self._screen, (255, 25, 25), center, radius)

        pygame.display.flip()

    def play_video_loop(
        self,
        path: Path,
        stop_event: threading.Event,
        interrupt_event: threading.Event,
    ) -> bool:
        """Loop a saved video; return True when the user requests app exit."""
        while not stop_event.is_set() and not interrupt_event.is_set():
            frames_played = 0
            with av.open(str(path)) as container:
                stream = container.streams.video[0]
                stream.thread_type = "AUTO"
                frame_rate = (
                    float(stream.average_rate)
                    if stream.average_rate is not None
                    else 24.0
                )
                playback_started = time.monotonic()
                first_frame_time: float | None = None

                for frame_index, frame in enumerate(container.decode(stream)):
                    if stop_event.is_set() or interrupt_event.is_set():
                        return False
                    if self.poll_exit_requested():
                        return True

                    if frame.time is not None:
                        if first_frame_time is None:
                            first_frame_time = frame.time
                        target_offset = frame.time - first_frame_time
                    else:
                        target_offset = frame_index / frame_rate

                    while True:
                        remaining = (
                            playback_started + target_offset - time.monotonic()
                        )
                        if remaining <= 0:
                            break
                        if stop_event.is_set() or interrupt_event.is_set():
                            return False
                        if self.poll_exit_requested():
                            return True
                        time.sleep(min(remaining, 0.02))

                    video_frame = frame.to_ndarray(format="bgr24")
                    self.show_preview(video_frame)
                    frames_played += 1

            if frames_played == 0:
                raise RuntimeError(f"Video contains no decodable frames: {path}")

        return False

    def show_timed_message(
        self,
        title: str,
        detail: str,
        duration: float,
        stop_event: threading.Event,
    ) -> bool:
        """Show a full-screen message; return True when the user requests exit."""
        self._screen.fill((12, 12, 12))
        title_font = pygame.font.Font(None, max(40, min(self._size) // 9))
        detail_font = pygame.font.Font(None, max(24, min(self._size) // 18))
        title_surface = title_font.render(title, True, (255, 90, 90))
        detail_surface = detail_font.render(detail, True, (235, 235, 235))
        center_x = self._size[0] // 2
        center_y = self._size[1] // 2
        self._screen.blit(
            title_surface,
            title_surface.get_rect(center=(center_x, center_y - 30)),
        )
        self._screen.blit(
            detail_surface,
            detail_surface.get_rect(center=(center_x, center_y + 35)),
        )
        pygame.display.flip()

        deadline = time.monotonic() + duration
        while time.monotonic() < deadline and not stop_event.is_set():
            if self.poll_exit_requested():
                return True
            time.sleep(0.02)
        return False

    def limit_frame_rate(self, frame_rate: int) -> None:
        self._clock.tick(frame_rate)

    def close(self) -> None:
        pygame.mouse.set_visible(True)
        pygame.quit()

    def _scale_to_cover(
        self,
        source: pygame.Surface,
        *,
        smooth: bool,
    ) -> pygame.Surface:
        source_width, source_height = source.get_size()
        target_width, target_height = self._size
        source_ratio = source_width / source_height
        target_ratio = target_width / target_height

        if source_ratio > target_ratio:
            crop_width = round(source_height * target_ratio)
            crop_rect = pygame.Rect(
                (source_width - crop_width) // 2,
                0,
                crop_width,
                source_height,
            )
        else:
            crop_height = round(source_width / target_ratio)
            crop_rect = pygame.Rect(
                0,
                (source_height - crop_height) // 2,
                source_width,
                crop_height,
            )

        cropped = source.subsurface(crop_rect)
        scaler = pygame.transform.smoothscale if smooth else pygame.transform.scale
        return scaler(cropped, self._size)

    def _show_empty_state(self) -> None:
        self._screen.fill((0, 0, 0))
        font_size = max(24, min(self._size) // 14)
        font = pygame.font.Font(None, font_size)
        message = font.render("Press capture to take a picture", True, (235, 235, 235))
        position = message.get_rect(
            center=(self._size[0] // 2, self._size[1] // 2)
        )
        self._screen.blit(message, position)
