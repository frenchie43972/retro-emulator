"""Reusable pygame-backed window renderer for platform framebuffers."""

from __future__ import annotations

from dataclasses import dataclass

from emulator.interfaces import FrameBuffer, VideoOutput
from emulator.io import KeyboardInputProvider


class PygameUnavailableError(RuntimeError):
    """Raised when pygame is required but not installed."""


@dataclass
class PygameWindowRenderer(VideoOutput):
    """Render framebuffer updates to a scaled window and forward keyboard events."""

    width: int
    height: int
    scale: int = 3
    title: str = "Retro Emulator"
    input_provider: KeyboardInputProvider | None = None

    def __post_init__(self) -> None:
        try:
            import pygame
        except ImportError as exc:  # pragma: no cover - exercised by import-failure tests
            raise PygameUnavailableError(
                "pygame is not installed. Install it with: pip install pygame"
            ) from exc

        self._pygame = pygame
        self._window = None
        self._running = True
        self._key_map = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_z: "z",
            pygame.K_x: "x",
            pygame.K_RETURN: "enter",
            pygame.K_RSHIFT: "right shift",
        }

        pygame.init()
        pygame.display.set_caption(self.title)
        self._window = pygame.display.set_mode((self.width * self.scale, self.height * self.scale))

    def render_frame(self, framebuffer: FrameBuffer) -> None:
        """Render one RGB/RGBA framebuffer to the host window."""
        self._process_events()
        if not self._running:
            return

        pixel_count = framebuffer.width * framebuffer.height
        bytes_per_pixel = len(framebuffer.pixels) // pixel_count if pixel_count else 0
        if bytes_per_pixel == 3:
            pixel_format = "RGB"
        else:
            pixel_format = "RGBA"

        surface = self._pygame.image.frombuffer(
            framebuffer.pixels,
            (framebuffer.width, framebuffer.height),
            pixel_format,
        )
        scaled = self._pygame.transform.scale(
            surface,
            (framebuffer.width * self.scale, framebuffer.height * self.scale),
        )
        self._window.blit(scaled, (0, 0))
        self._pygame.display.flip()

    def display(self, frame: FrameBuffer) -> None:
        """VideoOutput compatibility entrypoint used by EmulatorRuntime."""
        self.render_frame(frame)

    def _process_events(self) -> None:
        for event in self._pygame.event.get():
            if event.type == self._pygame.QUIT:
                self._running = False
                continue

            if self.input_provider is None:
                continue

            if event.type == self._pygame.KEYDOWN and event.key in self._key_map:
                self.input_provider.set_key_state(self._key_map[event.key], True)
            elif event.type == self._pygame.KEYUP and event.key in self._key_map:
                self.input_provider.set_key_state(self._key_map[event.key], False)

    def exit_requested(self) -> bool:
        return not self._running

    def shutdown(self) -> None:
        self._pygame.quit()

