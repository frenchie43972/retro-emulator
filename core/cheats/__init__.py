"""Cheat framework shared by emulator platforms."""

from .cheat_decoder import CheatDecodeError, DecodedCheat, decode_game_genie
from .cheat_manager import CheatManager
from .cheat_patch import CheatPatch

__all__ = [
    "CheatDecodeError",
    "CheatManager",
    "CheatPatch",
    "DecodedCheat",
    "decode_game_genie",
]
