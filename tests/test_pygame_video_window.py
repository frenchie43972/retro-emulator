import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime
from frontend.video import PygameUnavailableError, PygameWindowRenderer


def make_bootable_ines_rom(*, reset_vector: int = 0xC000) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([1, 0, 0x00, 0x00])
    header.extend(b"\x00" * 8)

    prg = bytearray([0xEA] * 0x4000)
    prg[reset_vector - 0xC000] = 0xA9
    prg[reset_vector - 0xC000 + 1] = 0x42
    prg[0x3FFC] = reset_vector & 0xFF
    prg[0x3FFD] = (reset_vector >> 8) & 0xFF

    return bytes(header) + bytes(prg)


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
    K_ESCAPE = 9

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
    def test_window_initializes_and_renders_nes_frames_continuously(self):
        fake_pygame = _FakePygame()
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            video = PygameWindowRenderer(width=256, height=240, scale=3, title="NES")
            platform = PluginLoader().load("nes")
            runtime = EmulatorRuntime(
                platform=platform,
                video_output=video,
                audio_output=SimpleNamespace(play=lambda _samples: None),
                input_provider=SimpleNamespace(poll=lambda: {}),
            )
            runtime.initialize(make_bootable_ines_rom())
            runtime.run_frame()
            runtime.run_frame()

        self.assertEqual(fake_pygame.display_mode, (768, 720))
        self.assertGreaterEqual(fake_pygame.flip_count, 2)
        self.assertIsNotNone(fake_pygame.window.last_surface)

    def test_escape_requests_return_to_browser(self):
        fake_pygame = _FakePygame()
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            video = PygameWindowRenderer(width=256, height=240, scale=3, title="NES")
            fake_pygame._events = [SimpleNamespace(type=fake_pygame.KEYDOWN, key=fake_pygame.K_ESCAPE)]
            video._process_events()

        self.assertTrue(video.browser_exit_requested())


    def test_keyboard_events_update_input_provider_state(self):
        fake_pygame = _FakePygame()
        input_provider = SimpleNamespace(
            key_down=lambda key: input_provider.state.__setitem__(key, True),
            key_up=lambda key: input_provider.state.__setitem__(key, False),
            state={},
        )
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            video = PygameWindowRenderer(width=256, height=240, scale=3, title="NES", input_provider=input_provider)
            fake_pygame._events = [
                SimpleNamespace(type=fake_pygame.KEYDOWN, key=fake_pygame.K_RSHIFT),
                SimpleNamespace(type=fake_pygame.KEYDOWN, key=fake_pygame.K_UP),
                SimpleNamespace(type=fake_pygame.KEYUP, key=fake_pygame.K_UP),
            ]
            video._process_events()

        self.assertTrue(input_provider.state["right shift"])
        self.assertFalse(input_provider.state["up"])

    def test_missing_pygame_dependency_message(self):
        with patch.dict(sys.modules, {"pygame": None}):
            with self.assertRaises(PygameUnavailableError) as ctx:
                PygameWindowRenderer(width=256, height=240)
        self.assertIn("pip install pygame", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
