"""Basic TurboGrafx-16 PSG implementation with CPU-mapped registers."""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.interfaces import AudioProcessor, MemoryDevice

from .audio_mixer import mix_channel_samples
from .psg_channel import PSGChannel

CPU_CLOCK_HZ = 7_159_090
CHANNEL_COUNT = 6
REG_CHANNEL_SELECT = 0x00
REG_GLOBAL_ENABLE = 0x01
REG_FREQ_LOW = 0x02
REG_FREQ_HIGH = 0x03
REG_VOLUME = 0x04
REG_CHANNEL_ENABLE = 0x05
REG_WAVE_INDEX = 0x06
REG_WAVE_DATA = 0x07


@dataclass
class TG16PSG(AudioProcessor, MemoryDevice):
    """Programmable sound generator used by the TurboGrafx-16."""

    sample_rate: int = 44_100
    channels: list[PSGChannel] = field(default_factory=lambda: [PSGChannel() for _ in range(CHANNEL_COUNT)])
    selected_channel: int = 0
    global_enable: bool = True
    _wave_write_index: list[int] = field(default_factory=lambda: [0] * CHANNEL_COUNT)
    _samples: list[float] = field(default_factory=list)
    _sample_accumulator: float = 0.0

    def reset(self) -> None:
        self.selected_channel = 0
        self.global_enable = True
        self._wave_write_index = [0] * CHANNEL_COUNT
        self._samples = []
        self._sample_accumulator = 0.0
        self.channels = [PSGChannel() for _ in range(CHANNEL_COUNT)]

    def step(self, cycles: int) -> None:
        if cycles <= 0:
            return

        self._sample_accumulator += cycles * (self.sample_rate / CPU_CLOCK_HZ)
        sample_count = int(self._sample_accumulator)
        self._sample_accumulator -= sample_count

        for _ in range(sample_count):
            if not self.global_enable:
                self._samples.append(0.0)
                continue
            self._samples.append(mix_channel_samples(channel.sample(self.sample_rate) for channel in self.channels))

    def pull_samples(self) -> list[float]:
        out = self._samples
        self._samples = []
        return out

    def read(self, address: int) -> int:
        reg = address & 0x0F
        channel = self.channels[self.selected_channel]

        if reg == REG_CHANNEL_SELECT:
            return self.selected_channel
        if reg == REG_GLOBAL_ENABLE:
            return int(self.global_enable)
        if reg == REG_FREQ_LOW:
            return channel.frequency & 0xFF
        if reg == REG_FREQ_HIGH:
            return (channel.frequency >> 8) & 0x0F
        if reg == REG_VOLUME:
            return channel.volume & 0x1F
        if reg == REG_CHANNEL_ENABLE:
            return int(channel.enabled)
        if reg == REG_WAVE_INDEX:
            return self._wave_write_index[self.selected_channel] & 0x1F
        if reg == REG_WAVE_DATA:
            index = self._wave_write_index[self.selected_channel]
            return channel.waveform.read(index)
        return 0xFF

    def write(self, address: int, value: int) -> None:
        reg = address & 0x0F
        value &= 0xFF

        if reg == REG_CHANNEL_SELECT:
            self.selected_channel = value % CHANNEL_COUNT
            return
        if reg == REG_GLOBAL_ENABLE:
            self.global_enable = bool(value & 0x01)
            return

        channel = self.channels[self.selected_channel]

        if reg == REG_FREQ_LOW:
            channel.frequency = (channel.frequency & 0x0F00) | value
        elif reg == REG_FREQ_HIGH:
            channel.frequency = ((value & 0x0F) << 8) | (channel.frequency & 0x00FF)
        elif reg == REG_VOLUME:
            channel.volume = value & 0x1F
        elif reg == REG_CHANNEL_ENABLE:
            channel.enabled = bool(value & 0x01)
            if not channel.enabled:
                channel.playback_position = 0.0
        elif reg == REG_WAVE_INDEX:
            self._wave_write_index[self.selected_channel] = value & 0x1F
        elif reg == REG_WAVE_DATA:
            index = self._wave_write_index[self.selected_channel]
            channel.waveform.write(index, value)
            self._wave_write_index[self.selected_channel] = (index + 1) & 0x1F
