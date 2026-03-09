"""ROM directory scanning and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.cartridge import CartridgeLoadError, CartridgeLoader

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
                if not rom_path.is_file() or rom_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
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
            cartridge = self.loader.load_file(path)
        except (CartridgeLoadError, OSError, PermissionError):
            return None

        try:
            rom_size = path.stat().st_size
            resolved_path = path.resolve()
        except OSError:
            return None

        format_name = cartridge.metadata.format_name.lower()
        platform = "nes" if format_name == "ines" else "unknown"
        return ROMMetadata(
            file_name=path.name,
            file_path=resolved_path,
            platform=platform,
            rom_size=rom_size,
            mapper=cartridge.metadata.mapper,
        )
