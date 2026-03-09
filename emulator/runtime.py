"""Central emulator runtime loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.save_states import SaveStateManager
from .interfaces import AudioOutput, InputProvider, VideoOutput
from .platform import Platform


@dataclass
class RuntimeConfig:
    """Runtime controls for stepping and frame pacing behavior."""

    cycles_per_frame: int = 29_780
    saves_root: Path = Path("saves")


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
        self.save_state_manager: SaveStateManager | None = None
        self._video_sink_connected = False
        self._clock = None

    def initialize(self, rom_bytes: bytes) -> None:
        """Load cartridge, map it into memory, and reset all components."""
        self.platform.cartridge.load(rom_bytes)
        self.platform.cartridge.attach_to_bus(self.platform.bus)
        self.platform.reset()
        self._initialize_save_system()
        self._connect_video_pipeline()
        self._load_persistent_ram_if_supported()

    def initialize_from_file(self, rom_path: str | Path) -> None:
        """Load a ROM by path to enable stable save slot/save RAM naming."""
        if not hasattr(self.platform.cartridge, "load_from_file"):
            raise TypeError("Platform cartridge does not support path-based loading")
        self.platform.cartridge.load_from_file(rom_path)
        self.platform.cartridge.attach_to_bus(self.platform.bus)
        self.platform.reset()
        self._initialize_save_system()
        self._connect_video_pipeline()
        self._load_persistent_ram_if_supported()

    def run_frame(self) -> None:
        """Run CPU/PPU/APU until the PPU reports a completed frame."""
        self._process_input()

        frame_rendered = False
        while not frame_rendered:
            cycles = self.platform.cpu.step(self.platform.bus)

            ppu = self._resolve_ppu()
            if ppu is not None:
                ppu_cycles = cycles * getattr(ppu, "ppu_cycles_per_cpu_cycle", 1)
                ppu.step(ppu_cycles)

            self.platform.audio.step(cycles)

            if self._frame_completed(ppu):
                frame = self._consume_completed_frame(ppu)
                frame_rendered = True
                if not self._video_sink_connected:
                    if hasattr(self.video_output, "render_frame"):
                        self.video_output.render_frame(frame)
                    else:
                        self.video_output.display(frame)
                self._pace_frame()

            samples = self.platform.audio.pull_samples()
            if samples:
                self.audio_output.play(samples)

    def save_state(self, slot_number: int) -> Path:
        if self.save_state_manager is None:
            raise RuntimeError("Save state manager not initialized")
        return self.save_state_manager.save_state(slot_number)

    def load_state(self, slot_number: int) -> Path:
        if self.save_state_manager is None:
            raise RuntimeError("Save state manager not initialized")
        return self.save_state_manager.load_state(slot_number)

    def shutdown(self) -> None:
        self._persist_ram_if_supported()
        if hasattr(self.video_output, "shutdown"):
            self.video_output.shutdown()

    def _process_input(self) -> None:
        key_states = self.input_provider.poll()
        for key, pressed in key_states.items():
            self.platform.controller.set_button_state(key, pressed)

    def _connect_video_pipeline(self) -> None:
        self._video_sink_connected = False
        if hasattr(self.platform.video, "set_frame_sink") and hasattr(self.video_output, "render_frame"):
            self.platform.video.set_frame_sink(self.video_output.render_frame)
            self._video_sink_connected = True
        if hasattr(self.video_output, "_pygame"):
            self._clock = self.video_output._pygame.time.Clock()

    def _initialize_save_system(self) -> None:
        rom_key = "default"
        if hasattr(self.platform.cartridge, "rom_key"):
            rom_key = self.platform.cartridge.rom_key()
        self.save_state_manager = SaveStateManager(
            platform=self.platform,
            rom_key=rom_key,
            save_root=self.config.saves_root,
        )

    def _load_persistent_ram_if_supported(self) -> None:
        if hasattr(self.platform.cartridge, "load_persistent_ram"):
            self.platform.cartridge.load_persistent_ram(self.config.saves_root)

    def _persist_ram_if_supported(self) -> None:
        if hasattr(self.platform.cartridge, "persist_ram"):
            self.platform.cartridge.persist_ram(self.config.saves_root)

    def _resolve_ppu(self):
        ppu = getattr(self.platform, "ppu", None)
        if ppu is not None and hasattr(ppu, "step"):
            return ppu

        if hasattr(self.platform.video, "step"):
            return self.platform.video

        return None

    def _frame_completed(self, ppu) -> bool:
        if ppu is None:
            return False
        if hasattr(ppu, "frame_complete"):
            return bool(ppu.frame_complete)
        if hasattr(ppu, "frame_ready"):
            return bool(ppu.frame_ready())
        return False

    def _consume_completed_frame(self, ppu):
        if ppu is not None and hasattr(ppu, "frame_complete"):
            ppu.frame_complete = False
            if hasattr(ppu, "framebuffer"):
                return ppu.framebuffer

        if hasattr(self.platform.video, "consume_frame"):
            return self.platform.video.consume_frame()

        if ppu is not None and hasattr(ppu, "_frame"):
            return ppu._frame

        raise RuntimeError("No frame source available after frame completion")

    def _pace_frame(self) -> None:
        if self._clock is not None:
            self._clock.tick(60)
