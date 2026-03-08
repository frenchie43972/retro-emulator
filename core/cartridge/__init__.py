"""Cartridge and ROM loading framework.

This package contains a format-agnostic cartridge abstraction and ROM parser
registry. New ROM formats can be added by registering additional parser
implementations in :class:`CartridgeLoader`.
"""

from .base import CartridgeMetadata, LoadedCartridge
from .loader import CartridgeLoader, CartridgeLoadError
from .mappers import Mapper0NROM

__all__ = [
    "CartridgeLoadError",
    "CartridgeLoader",
    "CartridgeMetadata",
    "LoadedCartridge",
    "Mapper0NROM",
]
