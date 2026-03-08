import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime, RuntimeConfig
from frontend.video import PygameUnavailableError, PygameVideoWindow


class _FakeWindow:
    def __init__(self):
        self.last_surface = None

    def blit(self, surface, pos):
        _ = pos
        self.last_surface = surface


class _FakePygame:
    QUIT = "QUIT"
    KEYDOWN = "KEYDOWN"
    KEYUP = "KEYUP"
    K_UP = 1
    K_DOWN = 2
    K_LEFT = 3
    K_RIGHT = 4
    K_z = 5
    K_x = 6
    K_RETURN = 7
    K_RSHIFT = 8

    def __init__(self):
        self.window = _FakeWindow()
        self.display_mode = None
        self.flip_count = 0
        self._events = []
        self.display = SimpleNamespace(
            set_caption=lambda _title: None,
            set_mode=self._set_mode,
            flip=self._flip,
        )
        self.transform = SimpleNamespace(scale=lambda surface, size: ("scaled", surface, size))
        self.image = SimpleNamespace(frombuffer=lambda pixels, size, fmt: ("surface", pixels, size, fmt))
        self.event = SimpleNamespace(get=self._get_events)

    def init(self):
        return None

    def quit(self):
        return None

    def _set_mode(self, size):
        self.display_mode = size
        return self.window

    def _flip(self):
        self.flip_count += 1

    def _get_events(self):
        events, self._events = self._events, []
        return events


class PygameVideoWindowTests(unittest.TestCase):
    def test_window_initializes_and_displays_runtime_frames(self):
        fake_pygame = _FakePygame()
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            video = PygameVideoWindow(width=160, height=144, scale=3, title="Test Window")
            platform = PluginLoader().load("null_platform")
            runtime = EmulatorRuntime(
                platform=platform,
                video_output=video,
                audio_output=SimpleNamespace(play=lambda _samples: None),
                input_provider=SimpleNamespace(poll=lambda: {}),
                config=RuntimeConfig(cycles_per_frame=10_000),
            )
            runtime.initialize(b"\x00" * 8)
            runtime.run_frame()

        self.assertEqual(fake_pygame.display_mode, (480, 432))
        self.assertEqual(fake_pygame.flip_count, 1)
        self.assertIsNotNone(fake_pygame.window.last_surface)

    def test_missing_pygame_dependency_message(self):
        with patch.dict(sys.modules, {"pygame": None}):
            with self.assertRaises(PygameUnavailableError) as ctx:
                PygameVideoWindow(width=256, height=240)
        self.assertIn("pip install pygame", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
