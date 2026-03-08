"""ROM launch orchestration from browser selection."""

from __future__ import annotations

from dataclasses import dataclass

from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime
from frontend.video import PygameUnavailableError, PygameVideoWindow

from .rom_library import ROMEntry


@dataclass
class LaunchResult:
    runtime: EmulatorRuntime
    platform_name: str


class ROMLauncher:
    """Loads selected ROMs, initializes platform runtime, and runs emulation."""

    def __init__(self, plugin_loader: PluginLoader | None = None) -> None:
        self.plugin_loader = plugin_loader or PluginLoader()

    def launch(self, rom: ROMEntry, *, max_frames: int = 0) -> LaunchResult:
        platform = self.plugin_loader.load(rom.platform)
        input_provider = KeyboardInputProvider()

        video_output = FrameBufferVideoOutput()
        if platform.name == "turbografx16":
            try:
                video_output = PygameVideoWindow(
                    width=256,
                    height=240,
                    scale=3,
                    title="TurboGrafx-16",
                    input_provider=input_provider,
                )
            except PygameUnavailableError as exc:
                print(exc)

        runtime = EmulatorRuntime(
            platform=platform,
            video_output=video_output,
            audio_output=BufferedAudioOutput(),
            input_provider=input_provider,
        )
        runtime.initialize_from_file(rom.file_path)

        for _ in range(max_frames):
            runtime.run_frame()

        return LaunchResult(runtime=runtime, platform_name=platform.name)
