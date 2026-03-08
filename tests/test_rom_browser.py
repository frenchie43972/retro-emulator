import tempfile
import unittest
from pathlib import Path

from frontend.rom_browser import ROMBrowserUI, ROMLauncher, ROMLibraryManager, ROMScanner


def make_ines_rom(
    *,
    prg_banks: int = 1,
    chr_banks: int = 1,
    mapper: int = 0,
    flags6: int = 0,
) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([prg_banks, chr_banks, (flags6 & 0x0F) | ((mapper & 0x0F) << 4), mapper & 0xF0])
    header.extend(b"\x00" * 8)
    prg = bytes((idx % 256 for idx in range(prg_banks * 0x4000)))
    chr_data = bytes((255 - (idx % 256) for idx in range(chr_banks * 0x2000)))
    return bytes(header) + prg + chr_data


class ROMBrowserTests(unittest.TestCase):
    def test_scanner_detects_valid_nes_roms(self):
        with tempfile.TemporaryDirectory() as td:
            rom_dir = Path(td)
            (rom_dir / "mario.nes").write_bytes(make_ines_rom())
            (rom_dir / "readme.txt").write_text("not a rom", encoding="utf-8")
            (rom_dir / "broken.nes").write_bytes(b"NOPE")

            scanner = ROMScanner()
            found = scanner.scan_directories([rom_dir])

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].file_name, "mario.nes")
            self.assertEqual(found[0].platform, "nes")
            self.assertEqual(found[0].mapper, 0)

    def test_launcher_initializes_nes_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            rom_path = Path(td) / "duckhunt.nes"
            rom_path.write_bytes(make_ines_rom(prg_banks=1, chr_banks=0))

            scanner = ROMScanner()
            library = ROMLibraryManager(scanner, [Path(td)])
            library.refresh()

            launcher = ROMLauncher()
            result = launcher.launch(library.selected_rom())

            self.assertEqual(result.platform_name, "nes")
            self.assertEqual(result.runtime.platform.bus.read(0x8000), 0x00)

    def test_ui_can_launch_and_return_to_browser(self):
        with tempfile.TemporaryDirectory() as td:
            rom_path = Path(td) / "zelda.nes"
            rom_path.write_bytes(make_ines_rom(prg_banks=1, chr_banks=0))

            library = ROMLibraryManager(ROMScanner(), [Path(td)])
            library.refresh()

            ui = ROMBrowserUI(library, ROMLauncher())
            launch_action = ui.handle_key(ROMBrowserUI.KEY_ENTER)
            self.assertEqual(launch_action.action, "launch")
            self.assertTrue(ui.in_game)

            return_action = ui.handle_key(ROMBrowserUI.KEY_ESCAPE)
            self.assertEqual(return_action.action, "return")
            self.assertFalse(ui.in_game)


if __name__ == "__main__":
    unittest.main()
