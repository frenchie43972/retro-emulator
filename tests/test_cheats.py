import unittest

from core.cheats import CheatDecodeError, CheatManager, decode_game_genie
from emulator.bus import MappedMemoryBus, RAM


class GameGenieDecodeTests(unittest.TestCase):
    def test_decodes_six_character_code(self):
        decoded = decode_game_genie("PAAAAA")
        self.assertEqual(decoded.address, 0x8000)
        self.assertEqual(decoded.value, 0x01)
        self.assertIsNone(decoded.compare)

    def test_decodes_eight_character_code_with_compare(self):
        decoded = decode_game_genie("PAAAAAAA")
        self.assertEqual(decoded.address, 0x8000)
        self.assertEqual(decoded.value, 0x01)
        self.assertEqual(decoded.compare, 0x00)

    def test_rejects_invalid_length(self):
        with self.assertRaisesRegex(CheatDecodeError, "Expected 6 or 8"):
            decode_game_genie("AAAAA")

    def test_rejects_invalid_characters(self):
        with self.assertRaisesRegex(CheatDecodeError, "Invalid Game Genie character"):
            decode_game_genie("AAAAA!")


class CheatMemoryPatchTests(unittest.TestCase):
    def test_active_cheat_patches_reads(self):
        bus = MappedMemoryBus()
        ram = RAM(0x10)
        bus.register(0x8000, 0x800F, ram)

        manager = CheatManager()
        bus.set_read_patcher(manager)
        bus.write(0x8000, 0x33)

        cheat = manager.add_cheat("PAAAAA")
        self.assertEqual(bus.read(0x8000), 0x01)
        self.assertEqual(manager.list_active_cheats(), [cheat])

    def test_disabling_cheat_restores_real_reads(self):
        bus = MappedMemoryBus()
        ram = RAM(0x10)
        bus.register(0x8000, 0x800F, ram)

        manager = CheatManager()
        bus.set_read_patcher(manager)
        bus.write(0x8000, 0x77)

        cheat = manager.add_cheat("PAAAAA")
        self.assertEqual(bus.read(0x8000), 0x01)
        manager.disable_cheat(cheat.id)
        self.assertEqual(bus.read(0x8000), 0x77)

    def test_compare_cheat_only_applies_when_original_matches(self):
        bus = MappedMemoryBus()
        ram = RAM(0x10)
        bus.register(0x8000, 0x800F, ram)

        manager = CheatManager()
        bus.set_read_patcher(manager)

        manager.add_cheat("PAAAAAAA")
        bus.write(0x8000, 0x22)
        self.assertEqual(bus.read(0x8000), 0x22)

        bus.write(0x8000, 0x00)
        self.assertEqual(bus.read(0x8000), 0x01)


if __name__ == "__main__":
    unittest.main()
