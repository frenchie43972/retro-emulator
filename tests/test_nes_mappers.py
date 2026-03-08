import unittest

from core.cartridge import CartridgeLoader


def make_ines_rom(*, prg_banks: int, chr_banks: int, mapper: int, flags6: int = 0, chr_fill_by_bank: bool = False) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([prg_banks, chr_banks, (flags6 & 0x0F) | ((mapper & 0x0F) << 4), mapper & 0xF0])
    header.extend(b"\x00" * 8)

    prg = bytearray()
    for bank in range(prg_banks):
        prg.extend(bytes([bank & 0xFF]) * 0x4000)

    chr_data = bytearray()
    for bank in range(chr_banks):
        if chr_fill_by_bank:
            chr_data.extend(bytes([(bank * 2 * 0x11) & 0xFF]) * 0x1000)
            chr_data.extend(bytes([((bank * 2 + 1) * 0x11) & 0xFF]) * 0x1000)
        else:
            chr_data.extend(bytes([bank & 0xFF]) * 0x2000)

    return bytes(header) + bytes(prg) + bytes(chr_data)


class Mapper1MMC1Tests(unittest.TestCase):
    def test_prg_bank_switching(self):
        loader = CartridgeLoader()
        cart = loader.load_bytes(make_ines_rom(prg_banks=4, chr_banks=2, mapper=1))

        self.assertEqual(cart.read(0xC000), 0x03)  # default fixed last bank
        self._mmc1_write_reg(cart, 0xE000, 0x02)
        self.assertEqual(cart.read(0x8000), 0x02)
        self.assertEqual(cart.read(0xC000), 0x03)

    def test_chr_bank_switching_and_mirroring(self):
        loader = CartridgeLoader()
        cart = loader.load_bytes(
            make_ines_rom(prg_banks=2, chr_banks=4, mapper=1, chr_fill_by_bank=True)
        )

        self._mmc1_write_reg(cart, 0x8000, 0x10)  # CHR 4KB mode + mirroring bits 0
        self._mmc1_write_reg(cart, 0xA000, 0x01)  # CHR bank 0 -> bank 1
        self._mmc1_write_reg(cart, 0xC000, 0x02)  # CHR bank 1 -> bank 2

        self.assertEqual(cart.ppu_read(0x0000), 0x11)
        self.assertEqual(cart.ppu_read(0x1000), 0x22)
        self.assertEqual(cart.mirroring(), "single0")

    @staticmethod
    def _mmc1_write_reg(cart, address: int, value: int) -> None:
        for bit in range(5):
            cart.write(address, (value >> bit) & 1)


class Mapper2UxROMTests(unittest.TestCase):
    def test_uxrom_prg_switching(self):
        loader = CartridgeLoader()
        cart = loader.load_bytes(make_ines_rom(prg_banks=4, chr_banks=0, mapper=2))

        self.assertEqual(cart.read(0x8000), 0x00)
        self.assertEqual(cart.read(0xC000), 0x03)

        cart.write(0x8000, 0x02)
        self.assertEqual(cart.read(0x8000), 0x02)
        self.assertEqual(cart.read(0xC000), 0x03)


class Mapper3CNROMTests(unittest.TestCase):
    def test_cnrom_chr_switching(self):
        loader = CartridgeLoader()
        cart = loader.load_bytes(make_ines_rom(prg_banks=2, chr_banks=4, mapper=3, chr_fill_by_bank=True))

        self.assertEqual(cart.ppu_read(0x0010), 0x00)
        cart.write(0x8000, 0x02)
        self.assertEqual(cart.ppu_read(0x0010), 0x44)


if __name__ == "__main__":
    unittest.main()
