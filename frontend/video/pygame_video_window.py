"""Pygame-backed host video window for emulator framebuffers."""

from __future__ import annotations

from dataclasses import dataclass
from emulator.interfaces import FrameBuffer, VideoOutput
from emulator.io import KeyboardInputProvider


class PygameUnavailableError(RuntimeError):
    """Raised when pygame is required but not installed."""


@dataclass
class PygameVideoWindow(VideoOutput):
    """Render RGBA framebuffers to a scaled pygame window and forward input."""

    width: int
    height: int
    scale: int = 3
    title: str = "Retro Emulator"
    input_provider: KeyboardInputProvider | None = None

    def __post_init__(self) -> None:
        try:
            import pygame
        except ImportError as exc:  # pragma: no cover - validated by tests via exception text
            raise PygameUnavailableError(
                "pygame is not installed. Install it with: pip install pygame"
            ) from exc

        self._pygame = pygame
        self._window = None
        self._running = True
        self._key_map = {
            pygame.K_UP: "UP",
            pygame.K_DOWN: "DOWN",
            pygame.K_LEFT: "LEFT",
            pygame.K_RIGHT: "RIGHT",
            pygame.K_z: "A",
            pygame.K_x: "B",
            pygame.K_RETURN: "START",
            pygame.K_RSHIFT: "SELECT",
        }

        pygame.init()
        pygame.display.set_caption(self.title)
        self._window = pygame.display.set_mode((self.width * self.scale, self.height * self.scale))

    def display(self, frame: FrameBuffer) -> None:
        self._process_events()
        if not self._running:
            return

        surface = self._pygame.image.frombuffer(frame.pixels, (frame.width, frame.height), "RGBA")
        scaled = self._pygame.transform.scale(surface, (frame.width * self.scale, frame.height * self.scale))
        self._window.blit(scaled, (0, 0))
        self._pygame.display.flip()

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
