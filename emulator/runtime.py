"""Central emulator runtime loop."""

from __future__ import annotations

from dataclasses import dataclass

from .interfaces import AudioOutput, InputProvider, VideoOutput
from .platform import Platform


@dataclass
class RuntimeConfig:
    """Runtime controls for stepping and frame pacing behavior."""

    cycles_per_frame: int = 29_780


class EmulatorRuntime:
    """Coordinates CPU execution, video/audio generation, and input handling."""

    def __init__(
        self,
        platform: Platform,
        video_output: VideoOutput,
        audio_output: AudioOutput,
        input_provider: InputProvider,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.platform = platform
        self.video_output = video_output
        self.audio_output = audio_output
        self.input_provider = input_provider
        self.config = config or RuntimeConfig()

    def initialize(self, rom_bytes: bytes) -> None:
        """Load cartridge and reset all platform components."""
        self.platform.cartridge.load(rom_bytes)
        self.platform.reset()

    def run_frame(self) -> None:
        """Run enough CPU cycles to produce one video frame."""
        self._process_input()

        consumed = 0
        while consumed < self.config.cycles_per_frame:
            cycles = self.platform.cpu.step(self.platform.bus)
            consumed += cycles
            self.platform.video.step(cycles)
            self.platform.audio.step(cycles)

            if self.platform.video.frame_ready():
                self.video_output.display(self.platform.video.consume_frame())

            samples = self.platform.audio.pull_samples()
            if samples:
                self.audio_output.play(samples)

    def _process_input(self) -> None:
        key_states = self.input_provider.poll()
        for key, pressed in key_states.items():
            self.platform.controller.set_button_state(key, pressed)
