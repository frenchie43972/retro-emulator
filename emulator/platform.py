"""Platform composition model.

A platform bundles CPU/GPU/APU/controllers/cartridge and configures the shared
memory bus layout for a specific console family.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bus import MappedMemoryBus
from .interfaces import AudioProcessor, CPU, Cartridge, Controller, VideoProcessor


@dataclass
class Platform:
    """Container for one platform plugin implementation."""

    name: str
    cpu: CPU
    video: VideoProcessor
    audio: AudioProcessor
    cartridge: Cartridge
    controller: Controller
    bus: MappedMemoryBus

    def reset(self) -> None:
        self.cpu.reset()
        self.video.reset()
        self.audio.reset()


class PlatformFactory:
    """Factory contract implemented by plugin modules."""

    def create(self) -> Platform:  # pragma: no cover - interface method
        raise NotImplementedError
