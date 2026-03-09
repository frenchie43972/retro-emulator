"""ROM directory scanning and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.cartridge import CartridgeLoader

SUPPORTED_EXTENSIONS = {".nes"}


@dataclass(frozen=True)
class ROMMetadata:
    file_name: str
    file_path: Path
    platform: str
    rom_size: int
    mapper: int | None


class ROMScanner:
    """Scans configured directories for ROM files and extracts metadata."""

    def __init__(self, loader: CartridgeLoader | None = None) -> None:
        self.loader = loader or CartridgeLoader()

    def scan_directories(self, directories: list[Path], recursive: bool = True) -> list[ROMMetadata]:
        discovered: list[ROMMetadata] = []
        seen_paths: set[Path] = set()

        for directory in directories:
            if not directory.exists() or not directory.is_dir():
                continue

            candidates = directory.rglob("*") if recursive else directory.iterdir()
            for rom_path in sorted(candidates):
                if (
                    not rom_path.is_file()
                    or rom_path.name.startswith(".")
                    or rom_path.suffix.lower() not in SUPPORTED_EXTENSIONS
                ):
                    continue
                resolved = rom_path.resolve()
                if resolved in seen_paths:
                    continue
                metadata = self._extract_metadata(rom_path)
                if metadata is not None:
                    discovered.append(metadata)
                    seen_paths.add(resolved)
        return discovered

    def _extract_metadata(self, path: Path) -> ROMMetadata | None:
        try:
            rom_bytes = path.read_bytes()
            rom_size = len(rom_bytes)
            resolved_path = path.resolve()
        except (OSError, PermissionError):
            return None

        if len(rom_bytes) < 16 or rom_bytes[:4] != b"NES\x1A":
            return None

        header = rom_bytes[:16]
        prg_banks = header[4]
        chr_banks = header[5]
        flags6 = header[6]
        flags7 = header[7]
        mapper = (flags7 & 0xF0) | (flags6 >> 4)

        trainer_size = 512 if (flags6 & 0x04) else 0
        expected_size = 16 + trainer_size + (prg_banks * 0x4000) + (chr_banks * 0x2000)
        if rom_size < expected_size:
            return None

        return ROMMetadata(
            file_name=path.name,
            file_path=resolved_path,
            platform="nes",
            rom_size=rom_size,
            mapper=mapper,
        )
