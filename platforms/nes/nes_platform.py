"""NES platform assembly and startup wiring."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.cartridge import CartridgeLoader
from core.cartridge.base import LoadedCartridge
from core.cheats import CheatManager
from emulator.interfaces import Cartridge, MemoryBus
from emulator.platform import Platform

from .apu import NESAPU
from .cpu_6502 import MOS6502CPU
from .input.nes_controller import NESController
from .nes_memory_map import NESMemoryBus, NESMemoryMap
from .ppu import NESPPU


@dataclass
class NESCartridge(Cartridge):
    loader: CartridgeLoader = field(default_factory=CartridgeLoader)
    loaded: LoadedCartridge | None = None
    rom_path: Path | None = None
    _rom_fingerprint: str | None = None

    def load(self, rom_bytes: bytes) -> None:
        self.loaded = self.loader.load_bytes(rom_bytes)
        self.rom_path = None
        self._rom_fingerprint = hashlib.sha1(rom_bytes).hexdigest()[:16]

    def load_from_file(self, path: str | Path) -> None:
        rom_path = Path(path)
        rom_bytes = rom_path.read_bytes()
        self.loaded = self.loader.load_bytes(rom_bytes)
        self.rom_path = rom_path
        self._rom_fingerprint = hashlib.sha1(rom_bytes).hexdigest()[:16]

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

    def rom_key(self) -> str:
        if self.rom_path is not None:
            return self.rom_path.stem
        if self._rom_fingerprint is not None:
            return self._rom_fingerprint
        return "unknown"

    def save_ram_path(self, saves_root: Path | None = None) -> Path:
        base = saves_root or Path("saves")
        return base / self.rom_key() / "battery.sav"

    def load_persistent_ram(self, saves_root: Path | None = None) -> None:
        if self.loaded is None or not self.loaded.metadata.has_battery_ram:
            return
        path = self.save_ram_path(saves_root)
        if not path.exists():
            return
        self.loaded.load_ram(path)

    def persist_ram(self, saves_root: Path | None = None) -> None:
        if self.loaded is None or not self.loaded.metadata.has_battery_ram:
            return
        path = self.save_ram_path(saves_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.loaded.save_ram(path)


class NESPlatform(Platform):
    """Platform with NES-specific memory map reset behavior."""

    def __init__(self, *, debug: bool = False, saves_root: Path | None = None) -> None:
        self.memory_bus = NESMemoryBus(debug=debug)
        self.cheats = CheatManager()
        self.memory_bus.set_read_patcher(self.cheats)
        self.ppu = NESPPU()
        self.apu = NESAPU()
        self.controller = NESController()
        self.memory_map = NESMemoryMap(self.memory_bus, self.ppu, self.controller, self.apu)
        self.memory_map.attach()
        self.saves_root = saves_root or Path("saves")
        super().__init__(
            name="nes",
            cpu=MOS6502CPU(self.memory_bus, debug=debug),
            video=self.ppu,
            audio=self.apu,
            cartridge=NESCartridge(),
            controller=self.controller,
            bus=self.memory_bus,
        )

    def reset(self) -> None:
        self.memory_map.reset()
        self.ppu.set_cartridge(self.cartridge.loaded)
        super().reset()

    def capture_state(self) -> dict:
        loaded = self.cartridge.loaded
        if loaded is None:
            raise RuntimeError("Cannot save state without a loaded cartridge")
        return {
            "cpu": self.cpu.serialize_state(),
            "ram": self.memory_map.serialize_state(),
            "ppu": self.ppu.serialize_state(),
            "apu": self.apu.serialize_state(),
            "cartridge": loaded.serialize_state(),
            "controller": self.controller.serialize_state(),
        }

    def restore_state(self, state: dict) -> None:
        loaded = self.cartridge.loaded
        if loaded is None:
            raise RuntimeError("Cannot load state without a loaded cartridge")
        loaded.deserialize_state(state["cartridge"])
        self.memory_map.deserialize_state(state["ram"])
        self.ppu.deserialize_state(state["ppu"])
        self.apu.deserialize_state(state["apu"])
        self.controller.deserialize_state(state["controller"])
        self.cpu.deserialize_state(state["cpu"])


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
