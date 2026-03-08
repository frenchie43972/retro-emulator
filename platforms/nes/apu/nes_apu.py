"""Simplified NES APU implementation with CPU register interface."""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.interfaces import AudioProcessor, MemoryDevice

from .audio_mixer import mix_channels
from .dmc_channel import DMCChannel
from .noise_channel import NoiseChannel
from .pulse_channel import PulseChannel
from .triangle_channel import TriangleChannel

CPU_CLOCK_HZ = 1_789_773


@dataclass
class NESAPU(AudioProcessor, MemoryDevice):
    sample_rate: int = 44_100
    pulse1: PulseChannel = field(default_factory=PulseChannel)
    pulse2: PulseChannel = field(default_factory=PulseChannel)
    triangle: TriangleChannel = field(default_factory=TriangleChannel)
    noise: NoiseChannel = field(default_factory=NoiseChannel)
    dmc: DMCChannel = field(default_factory=DMCChannel)
    frame_counter_mode: int = 0
    irq_inhibit: bool = False
    _samples: list[float] = field(default_factory=list)
    _sample_accumulator: float = 0.0

    def reset(self) -> None:
        self._samples = []
        self._sample_accumulator = 0.0
        self.frame_counter_mode = 0
        self.irq_inhibit = False
        self.pulse1 = PulseChannel()
        self.pulse2 = PulseChannel()
        self.triangle = TriangleChannel()
        self.noise = NoiseChannel()
        self.dmc = DMCChannel()

    def step(self, cycles: int) -> None:
        if cycles <= 0:
            return
        self._sample_accumulator += cycles * (self.sample_rate / CPU_CLOCK_HZ)
        sample_count = int(self._sample_accumulator)
        self._sample_accumulator -= sample_count

        for _ in range(sample_count):
            self._samples.append(
                mix_channels(
                    pulse1=self.pulse1.sample(self.sample_rate),
                    pulse2=self.pulse2.sample(self.sample_rate),
                    triangle=self.triangle.sample(self.sample_rate),
                    noise=self.noise.sample(self.sample_rate),
                    dmc=self.dmc.sample(self.sample_rate),
                )
            )

    def pull_samples(self) -> list[float]:
        out = self._samples
        self._samples = []
        return out

    def read(self, address: int) -> int:
        if address == 0x15:
            status = 0
            status |= int(self.pulse1.length_counter > 0)
            status |= int(self.pulse2.length_counter > 0) << 1
            status |= int(self.triangle.length_counter > 0) << 2
            status |= int(self.noise.length_counter > 0) << 3
            status |= int(self.dmc.enabled) << 4
            return status
        return 0

    def write(self, address: int, value: int) -> None:
        value &= 0xFF

        if address == 0x00:
            self.pulse1.write_control(value)
        elif address == 0x02:
            self.pulse1.write_timer_low(value)
        elif address == 0x03:
            self.pulse1.write_timer_high(value)
        elif address == 0x04:
            self.pulse2.write_control(value)
        elif address == 0x06:
            self.pulse2.write_timer_low(value)
        elif address == 0x07:
            self.pulse2.write_timer_high(value)
        elif address == 0x08:
            self.triangle.write_linear_control(value)
        elif address == 0x0A:
            self.triangle.write_timer_low(value)
        elif address == 0x0B:
            self.triangle.write_timer_high(value)
        elif address == 0x0C:
            self.noise.write_control(value)
        elif address == 0x0E:
            self.noise.write_period(value)
        elif address == 0x0F:
            self.noise.write_length(value)
        elif address == 0x10:
            self.dmc.write_control(value)
        elif address == 0x11:
            self.dmc.write_direct_load(value)
        elif address == 0x12:
            self.dmc.write_sample_address(value)
        elif address == 0x13:
            self.dmc.write_sample_length(value)
        elif address == 0x15:
            self._write_status(value)

    def write_frame_counter(self, value: int) -> None:
        self.frame_counter_mode = (value >> 7) & 0x01
        self.irq_inhibit = bool((value >> 6) & 0x01)

    def _write_status(self, value: int) -> None:
        self.pulse1.set_enabled(bool(value & 0x01))
        self.pulse2.set_enabled(bool(value & 0x02))
        self.triangle.set_enabled(bool(value & 0x04))
        self.noise.set_enabled(bool(value & 0x08))
        self.dmc.set_enabled(bool(value & 0x10))


    def serialize_state(self) -> dict:
        return {
            "sample_rate": self.sample_rate,
            "pulse1": self.pulse1.serialize_state(),
            "pulse2": self.pulse2.serialize_state(),
            "triangle": self.triangle.serialize_state(),
            "noise": self.noise.serialize_state(),
            "dmc": self.dmc.serialize_state(),
            "frame_counter_mode": self.frame_counter_mode,
            "irq_inhibit": self.irq_inhibit,
            "sample_accumulator": self._sample_accumulator,
        }

    def deserialize_state(self, state: dict) -> None:
        self.sample_rate = int(state["sample_rate"])
        self.frame_counter_mode = int(state["frame_counter_mode"])
        self.irq_inhibit = bool(state["irq_inhibit"])
        self._sample_accumulator = float(state["sample_accumulator"])
        self._samples = []
        self.pulse1.deserialize_state(state["pulse1"])
        self.pulse2.deserialize_state(state["pulse2"])
        self.triangle.deserialize_state(state["triangle"])
        self.noise.deserialize_state(state["noise"])
        self.dmc.deserialize_state(state["dmc"])
