"""Frontend video backends."""

from .pygame_video_window import PygameUnavailableError, PygameVideoWindow

__all__ = ["PygameVideoWindow", "PygameUnavailableError"]
