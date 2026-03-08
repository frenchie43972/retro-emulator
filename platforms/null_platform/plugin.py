"""No-op platform plugin used to validate runtime integration.

This is intentionally not a real console implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.bus import MappedMemoryBus, RAM, ROM
from emulator.interfaces import AudioProcessor, CPU, Cartridge, Controller, FrameBuffer, MemoryBus, VideoProcessor
from emulator.platform import Platform


class NullCPU(CPU):
    """CPU stub that fetches one opcode byte and burns one cycle."""

    def reset(self) -> None:
        self.pc = 0

    def step(self, bus: MappedMemoryBus) -> int:
        _opcode = bus.read(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return 1


class NullVideo(VideoProcessor):
    """Video stub that emits a blank frame every fixed cycle window."""

    def __init__(self) -> None:
        self._cycles = 0
        self._ready = False
        self._frame = FrameBuffer(width=160, height=144, pixels=b"\x00" * (160 * 144 * 4))

    def reset(self) -> None:
        self._cycles = 0
        self._ready = False

    def step(self, cycles: int) -> None:
        self._cycles += cycles
        if self._cycles >= 10_000:
            self._cycles = 0
            self._ready = True

    def frame_ready(self) -> bool:
        return self._ready

    def consume_frame(self) -> FrameBuffer:
        self._ready = False
        return self._frame


class NullAudio(AudioProcessor):
    """Audio stub generating silence samples in fixed batches."""

    def __init__(self) -> None:
        self._cycles = 0
        self._samples: list[float] = []

    def reset(self) -> None:
        self._cycles = 0
        self._samples.clear()

    def step(self, cycles: int) -> None:
        self._cycles += cycles
        if self._cycles >= 200:
            self._cycles = 0
            self._samples.extend([0.0] * 128)

    def pull_samples(self) -> list[float]:
        samples = self._samples
        self._samples = []
        return samples


@dataclass
class NullCartridge(Cartridge):
    """Holds a ROM image for mapping into the memory bus."""

    rom: bytes = b""

    def load(self, rom_bytes: bytes) -> None:
        self.rom = rom_bytes

    def read(self, address: int) -> int:
        if not self.rom:
            return 0x00
        return self.rom[address % len(self.rom)]

    def write(self, address: int, value: int) -> None:
        _ = address, value

    def attach_to_bus(self, bus: MemoryBus) -> None:
        _ = bus


@dataclass
class NullController(Controller):
    """Simple controller state map keyed by generic button names."""

    state: dict[str, bool] = field(default_factory=dict)

    def set_button_state(self, button: str, pressed: bool) -> None:
        self.state[button] = pressed


class PlatformPlugin:
    """Factory expected by the dynamic plugin loader."""

    def create(self) -> Platform:
        bus = MappedMemoryBus()

        # Basic memory layout for reference and testing purposes.
        bus.register(0x0000, 0x7FFF, ROM(b"\xEA" * 0x8000))
        bus.register(0x8000, 0xFFFF, RAM(0x8000))

        return Platform(
            name="null_platform",
            cpu=NullCPU(),
            video=NullVideo(),
            audio=NullAudio(),
            cartridge=NullCartridge(),
            controller=NullController(),
            bus=bus,
        )
