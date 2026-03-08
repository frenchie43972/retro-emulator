"""NES platform assembly and startup wiring."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.cartridge import CartridgeLoader
from core.cartridge.base import LoadedCartridge
from emulator.interfaces import AudioProcessor, Cartridge, Controller, FrameBuffer, MemoryBus, VideoProcessor
from emulator.platform import Platform

from .cpu_6502 import MOS6502CPU
from .nes_memory_map import NESMemoryBus, NESMemoryMap


class NESVideo(VideoProcessor):
    def reset(self) -> None:
        self._ready = False
        self._frame = FrameBuffer(width=256, height=240, pixels=b"\x00" * (256 * 240 * 4))

    def step(self, cycles: int) -> None:
        self._ready = self._ready or cycles > 0

    def frame_ready(self) -> bool:
        return self._ready

    def consume_frame(self) -> FrameBuffer:
        self._ready = False
        return self._frame


class NESAudio(AudioProcessor):
    def reset(self) -> None:
        self._samples: list[float] = []

    def step(self, cycles: int) -> None:
        if cycles:
            self._samples.extend([0.0] * 8)

    def pull_samples(self) -> list[float]:
        out = self._samples
        self._samples = []
        return out


@dataclass
class NESCartridge(Cartridge):
    loader: CartridgeLoader = field(default_factory=CartridgeLoader)
    loaded: LoadedCartridge | None = None

    def load(self, rom_bytes: bytes) -> None:
        self.loaded = self.loader.load_bytes(rom_bytes)

    def load_from_file(self, path: str | Path) -> None:
        self.loaded = self.loader.load_file(path)

    def read(self, address: int) -> int:
        if self.loaded is None:
            raise RuntimeError("No cartridge loaded")
        return self.loaded.read(address)

    def write(self, address: int, value: int) -> None:
        if self.loaded is None:
            raise RuntimeError("No cartridge loaded")
        self.loaded.write(address, value)

    def attach_to_bus(self, bus: MemoryBus) -> None:
        if self.loaded is None:
            raise RuntimeError("No cartridge loaded")
        if not isinstance(bus, NESMemoryBus):
            raise TypeError("NES cartridge requires NESMemoryBus")
        self.loaded.attach_to_bus(bus)


@dataclass
class NESController(Controller):
    state: dict[str, bool] = field(default_factory=dict)

    def set_button_state(self, button: str, pressed: bool) -> None:
        self.state[button] = pressed


class NESPlatform(Platform):
    """Platform with NES-specific memory map reset behavior."""

    def __init__(self, *, debug: bool = False) -> None:
        self.memory_bus = NESMemoryBus(debug=debug)
        self.memory_map = NESMemoryMap(self.memory_bus)
        self.memory_map.attach()
        super().__init__(
            name="nes",
            cpu=MOS6502CPU(self.memory_bus, debug=debug),
            video=NESVideo(),
            audio=NESAudio(),
            cartridge=NESCartridge(),
            controller=NESController(),
            bus=self.memory_bus,
        )

    def reset(self) -> None:
        self.memory_map.reset()
        super().reset()


class PlatformPlugin:
    """NES plugin wiring full NES memory map and mapper-based cartridge."""

    def __init__(self, debug: bool | None = None) -> None:
        if debug is None:
            debug = os.getenv("NES_DEBUG", "0") in {"1", "true", "TRUE", "on", "ON"}
        self.debug = debug
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)

    def create(self) -> Platform:
        return NESPlatform(debug=self.debug)
