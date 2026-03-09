import unittest
from types import SimpleNamespace
from unittest.mock import patch

from frontend.gui_rom_browser import GuiRomMenu, MenuInputHandler


class GuiRomBrowserTests(unittest.TestCase):
    def test_input_handler_maps_navigation_and_actions(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")

        handler = MenuInputHandler()

        self.assertEqual(handler.action_for_key(pygame.K_UP).name, "move")
        self.assertEqual(handler.action_for_key(pygame.K_UP).delta, -1)
        self.assertEqual(handler.action_for_key(pygame.K_DOWN).delta, 1)
        self.assertEqual(handler.action_for_key(pygame.K_RETURN).name, "launch")
        self.assertEqual(handler.action_for_key(pygame.K_r).name, "refresh")
        self.assertEqual(handler.action_for_key(pygame.K_ESCAPE).name, "exit")

    def test_menu_refreshes_library_before_each_render(self):
        fake_pygame = SimpleNamespace(
            QUIT=1,
            KEYDOWN=2,
            event=SimpleNamespace(get=lambda: [SimpleNamespace(type=1)]),
        )

        class StubLibrary:
            def __init__(self):
                self.roms = []
                self.selected_index = 99
                self.refresh_calls = 0

            def refresh(self):
                self.refresh_calls += 1
                self.roms = ["a", "b"]

        class StubRenderer:
            def __init__(self):
                self.initialized = False
                self.rendered = False
                self.shutdown_called = False

            def initialize(self):
                self.initialized = True

            def render(self, library):
                self.rendered = True
                assert library.refresh_calls > 0
                assert library.selected_index == 1

            def shutdown(self):
                self.shutdown_called = True

        library = StubLibrary()
        menu = GuiRomMenu(library=library, launcher=SimpleNamespace())
        renderer = StubRenderer()
        menu.renderer = renderer

        with patch.dict("sys.modules", {"pygame": fake_pygame}):
            menu.run()

        self.assertEqual(library.refresh_calls, 1)
        self.assertTrue(renderer.initialized)
        self.assertTrue(renderer.rendered)
        self.assertTrue(renderer.shutdown_called)


if __name__ == "__main__":
    unittest.main()
