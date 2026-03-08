"""TurboGrafx-16 platform assembly and cartridge integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.bus import MappedMemoryBus
from emulator.interfaces import Cartridge, MemoryBus
from emulator.platform import Platform
from platforms.null_platform.plugin import NullController

from .audio import TG16PSG
from .cpu_huc6280 import HuC6280CPU
from .hucard_loader import HuCardLoader, LoadedHuCard
from .tg16_memory_map import TG16MemoryMap
from .video import HuC6270VDC


@dataclass
class TurboGrafxCartridge(Cartridge):
    """TurboGrafx HuCard cartridge interface for the runtime."""

    loader: HuCardLoader = field(default_factory=HuCardLoader)
    loaded: LoadedHuCard | None = None

    def load(self, rom_bytes: bytes) -> None:
        self.loaded = self.loader.load_bytes(rom_bytes)

    def read(self, address: int) -> int:
        if self.loaded is None:
            raise RuntimeError("No HuCard loaded")
        return self.loaded.read_physical(address)

    def write(self, address: int, value: int) -> None:
        _ = address, value

    def attach_to_bus(self, bus: MemoryBus) -> None:
        _ = bus


class TurboGrafx16Platform(Platform):
    """Platform wiring for HuC6280 + HuCard + baseline TG16 memory map."""

    def __init__(self) -> None:
        bus = MappedMemoryBus()
        self.vdc = HuC6270VDC()
        self.psg = TG16PSG()
        self.memory_map = TG16MemoryMap.create(bus, self.vdc, self.psg)
        self.tg16_cartridge = TurboGrafxCartridge()
        super().__init__(
            name="turbografx16",
            cpu=HuC6280CPU(bus),
            video=self.vdc,
            audio=self.psg,
            cartridge=self.tg16_cartridge,
            controller=NullController(),
            bus=bus,
        )

    def reset(self) -> None:
        if self.tg16_cartridge.loaded is not None:
            self.memory_map.rom.load(self.tg16_cartridge.loaded)
        super().reset()
