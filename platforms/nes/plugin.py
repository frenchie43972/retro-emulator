"""NES platform integration for cartridge loading and NROM mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.cartridge import CartridgeLoader
from core.cartridge.base import LoadedCartridge
from emulator.bus import MappedMemoryBus, RAM
from emulator.interfaces import AudioProcessor, Cartridge, Controller, FrameBuffer, MemoryBus, VideoProcessor
from emulator.platform import Platform
from platforms.nes.cpu_6502 import MOS6502CPU


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
    """Platform cartridge facade backed by the generic cartridge subsystem."""

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
        if not isinstance(bus, MappedMemoryBus):
            raise TypeError("NES cartridge requires MappedMemoryBus")
        self.loaded.attach_to_bus(bus)

    def save_ram(self, path: str | Path) -> None:
        if self.loaded is not None:
            self.loaded.save_ram(Path(path))

    def load_ram(self, path: str | Path) -> None:
        if self.loaded is not None:
            self.loaded.load_ram(Path(path))


@dataclass
class NESController(Controller):
    state: dict[str, bool] = field(default_factory=dict)

    def set_button_state(self, button: str, pressed: bool) -> None:
        self.state[button] = pressed


class PlatformPlugin:
    """NES plugin wiring cartridge mapping into the bus."""

    def create(self) -> Platform:
        bus = MappedMemoryBus()
        bus.register(0x0000, 0x1FFF, RAM(0x2000))

        return Platform(
            name="nes",
            cpu=MOS6502CPU(bus),
            video=NESVideo(),
            audio=NESAudio(),
            cartridge=NESCartridge(),
            controller=NESController(),
            bus=bus,
        )
