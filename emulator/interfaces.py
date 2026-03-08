"""Core hardware interfaces for the emulator framework.

These abstract interfaces define contracts that each platform module must
implement to plug into the shared runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class FrameBuffer:
    """Simple RGBA framebuffer payload produced by a graphics processor."""

    width: int
    height: int
    pixels: bytes


class MemoryDevice(ABC):
    """Addressable memory mapped device exposed on a memory bus."""

    @abstractmethod
    def read(self, address: int) -> int:
        """Read one byte at a *device-local* address."""

    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """Write one byte to a *device-local* address."""


class MemoryBus(ABC):
    """Routing layer used by CPUs to access all mapped hardware."""

    @abstractmethod
    def read(self, address: int) -> int:
        """Read one byte at a global bus address."""

    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """Write one byte at a global bus address."""


class CPU(ABC):
    """Platform CPU implementation."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal CPU state."""

    @abstractmethod
    def step(self, bus: MemoryBus) -> int:
        """Execute one instruction and return consumed cycle count."""


class VideoProcessor(ABC):
    """Platform graphics processor implementation."""

    @abstractmethod
    def reset(self) -> None:
        """Reset graphics pipeline state."""

    @abstractmethod
    def step(self, cycles: int) -> None:
        """Advance the graphics processor by CPU cycle count."""

    @abstractmethod
    def frame_ready(self) -> bool:
        """Return True when a new frame can be consumed."""

    @abstractmethod
    def consume_frame(self) -> FrameBuffer:
        """Return the latest frame and clear the ready flag."""


class AudioProcessor(ABC):
    """Platform audio processor implementation."""

    @abstractmethod
    def reset(self) -> None:
        """Reset audio synthesis state."""

    @abstractmethod
    def step(self, cycles: int) -> None:
        """Advance audio synthesis by CPU cycle count."""

    @abstractmethod
    def pull_samples(self) -> list[float]:
        """Drain generated PCM samples from the processor."""


class Cartridge(ABC):
    """Platform cartridge/ROM interface."""

    @abstractmethod
    def load(self, rom_bytes: bytes) -> None:
        """Load ROM or cartridge image data."""

    @abstractmethod
    def read(self, address: int) -> int:
        """Read one byte from cartridge-mapped memory."""

    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """Write one byte to cartridge-mapped memory."""

    @abstractmethod
    def attach_to_bus(self, bus: "MemoryBus") -> None:
        """Register cartridge memory regions on a bus."""


class Controller(ABC):
    """Platform controller interface."""

    @abstractmethod
    def set_button_state(self, button: str, pressed: bool) -> None:
        """Set logical controller button state."""


class InputProvider(ABC):
    """Host input source abstraction (keyboard/gamepad/event queue)."""

    @abstractmethod
    def poll(self) -> dict[str, bool]:
        """Return a map of keyboard keys to pressed state."""


class VideoOutput(ABC):
    """Host video output backend interface."""

    @abstractmethod
    def display(self, frame: FrameBuffer) -> None:
        """Display one frame on the host system."""


class AudioOutput(ABC):
    """Host audio output backend interface."""

    @abstractmethod
    def play(self, samples: list[float]) -> None:
        """Play PCM samples on the host system."""
