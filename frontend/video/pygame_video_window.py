"""Backward-compatible import shim for pygame window renderer."""

from .pygame_window import PygameUnavailableError, PygameWindowRenderer

# Legacy name retained for compatibility.
PygameVideoWindow = PygameWindowRenderer

__all__ = ["PygameWindowRenderer", "PygameVideoWindow", "PygameUnavailableError"]
