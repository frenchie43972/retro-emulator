"""TurboGrafx-16 PSG waveform channel state and synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field

from .waveform_memory import WaveformMemory


@dataclass
class PSGChannel:
    """One programmable waveform voice from the six-channel TG16 PSG."""

    waveform: WaveformMemory = field(default_factory=WaveformMemory)
    enabled: bool = False
    frequency: int = 0
    volume: int = 0
    playback_position: float = 0.0

    def reset(self) -> None:
        self.enabled = False
        self.frequency = 0
        self.volume = 0
        self.playback_position = 0.0
        self.waveform = WaveformMemory()

    def sample(self, sample_rate: int) -> float:
        if not self.enabled or self.frequency <= 0 or self.volume == 0:
            return 0.0

        wave_sample = self.waveform.amplitude(self.playback_position)
        gain = self.volume / 31.0

        step = self.frequency / sample_rate
        self.playback_position = (self.playback_position + step) % 32.0
        return wave_sample * gain
