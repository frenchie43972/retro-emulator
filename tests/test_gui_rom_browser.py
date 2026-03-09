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

            @property
            def visible_rows(self):
                return 5

            def render(self, library, scroll_offset=0):
                self.rendered = True
                assert library.refresh_calls > 0
                assert library.selected_index == 1
                assert scroll_offset == 0

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


class GuiRomMenuScrollTests(unittest.TestCase):
    def test_scroll_offset_tracks_selected_index(self):
        library = SimpleNamespace(
            roms=[SimpleNamespace(file_name=f"ROM {i}") for i in range(20)],
            selected_index=0,
        )
        menu = GuiRomMenu(library=library, launcher=SimpleNamespace())
        menu.renderer = SimpleNamespace(visible_rows=5)

        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 0)

        library.selected_index = 4
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 0)

        library.selected_index = 5
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 1)

        library.selected_index = 10
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 6)

        library.selected_index = 2
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 2)

    def test_scroll_offset_clamps_to_bounds(self):
        library = SimpleNamespace(
            roms=[SimpleNamespace(file_name=f"ROM {i}") for i in range(3)],
            selected_index=2,
        )
        menu = GuiRomMenu(library=library, launcher=SimpleNamespace())
        menu.renderer = SimpleNamespace(visible_rows=5)

        menu.scroll_offset = 99
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 0)

        library.roms = []
        menu.scroll_offset = 4
        menu._sync_scroll_offset()
        self.assertEqual(menu.scroll_offset, 0)


if __name__ == "__main__":
    unittest.main()
