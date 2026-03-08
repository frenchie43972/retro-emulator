"""NES platform assembly and startup wiring."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.cartridge import CartridgeLoader
from core.cartridge.base import LoadedCartridge
from emulator.interfaces import AudioProcessor, Cartridge, MemoryBus
from emulator.platform import Platform

from .cpu_6502 import MOS6502CPU
from .input.nes_controller import NESController
from .nes_memory_map import NESMemoryBus, NESMemoryMap
from .ppu import NESPPU


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


class NESPlatform(Platform):
    """Platform with NES-specific memory map reset behavior."""

    def __init__(self, *, debug: bool = False) -> None:
        self.memory_bus = NESMemoryBus(debug=debug)
        self.ppu = NESPPU()
        self.controller = NESController()
        self.memory_map = NESMemoryMap(self.memory_bus, self.ppu, self.controller)
        self.memory_map.attach()
        super().__init__(
            name="nes",
            cpu=MOS6502CPU(self.memory_bus, debug=debug),
            video=self.ppu,
            audio=NESAudio(),
            cartridge=NESCartridge(),
            controller=self.controller,
            bus=self.memory_bus,
        )

    def reset(self) -> None:
        self.memory_map.reset()
        self.ppu.set_cartridge(self.cartridge.loaded)
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
