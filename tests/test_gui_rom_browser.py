import unittest

from frontend.gui_rom_browser import MenuInputHandler


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
        self.assertEqual(handler.action_for_key(pygame.K_ESCAPE).name, "exit")


if __name__ == "__main__":
    unittest.main()
