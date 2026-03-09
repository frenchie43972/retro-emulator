"""ROM library management for browsing and selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .rom_scanner import ROMMetadata, ROMScanner


@dataclass(frozen=True)
class ROMEntry:
    file_name: str
    file_path: Path
    platform: str
    rom_size: int
    mapper: int | None

    @classmethod
    def from_metadata(cls, metadata: ROMMetadata) -> "ROMEntry":
        return cls(
            file_name=metadata.file_name,
            file_path=metadata.file_path,
            platform=metadata.platform,
            rom_size=metadata.rom_size,
            mapper=metadata.mapper,
        )


class ROMLibraryManager:
    """Maintains discovered ROMs and selection state."""

    def __init__(self, scanner: ROMScanner, directories: list[Path]) -> None:
        self.scanner = scanner
        self.directories = directories
        self.roms: list[ROMEntry] = []
        self.selected_index = 0

    def refresh(self) -> list[ROMEntry]:
        metadata = self.scanner.scan_directories(self.directories)
        self.roms = sorted(
            (ROMEntry.from_metadata(item) for item in metadata),
            key=lambda rom: rom.file_name.lower(),
        )
        if not self.roms:
            self.selected_index = 0
        else:
            self.selected_index = min(self.selected_index, len(self.roms) - 1)
        return list(self.roms)

    def move_selection(self, delta: int) -> None:
        if not self.roms:
            self.selected_index = 0
            return
        self.selected_index = (self.selected_index + delta) % len(self.roms)

    def selected_rom(self) -> ROMEntry | None:
        if not self.roms:
            return None
        return self.roms[self.selected_index]
