"""Game Genie code decoding for NES-style cheats."""

from __future__ import annotations

from dataclasses import dataclass


class CheatDecodeError(ValueError):
    """Raised when a cheat code cannot be decoded."""


_ALPHABET = "APZLGITYEOXUKSVN"
_DECODE_TABLE = {char: value for value, char in enumerate(_ALPHABET)}


@dataclass(frozen=True)
class DecodedCheat:
    address: int
    value: int
    compare: int | None = None


def _decode_nibbles(code: str) -> list[int]:
    normalized = code.strip().upper()
    if len(normalized) not in (6, 8):
        raise CheatDecodeError(
            f"Invalid Game Genie code length {len(normalized)} for '{code}'. Expected 6 or 8 characters."
        )

    nibbles: list[int] = []
    for index, char in enumerate(normalized):
        nibble = _DECODE_TABLE.get(char)
        if nibble is None:
            raise CheatDecodeError(
                f"Invalid Game Genie character '{char}' at position {index + 1} in '{code}'."
            )
        nibbles.append(nibble)
    return nibbles


def decode_game_genie(code: str) -> DecodedCheat:
    """Decode a 6 or 8 character NES Game Genie code."""
    n = _decode_nibbles(code)

    # Bit arrangement follows the original NES Game Genie encoding.
    value = (n[0] & 0x7) | ((n[1] & 0x7) << 4) | (n[5] & 0x8)

    address = 0x8000
    address |= (n[2] & 0x7) << 4
    address |= (n[3] & 0x7) << 12
    address |= (n[4] & 0x7) << 8
    address |= n[5] & 0x7
    address |= (n[1] & 0x8) << 4
    address |= (n[2] & 0x8) << 8
    address |= (n[3] & 0x8) << 8
    address |= (n[4] & 0x8) << 8

    if len(n) == 6:
        return DecodedCheat(address=address, value=value)

    compare = (n[6] & 0x7) | ((n[7] & 0x7) << 4) | (n[5] & 0x8)
    return DecodedCheat(address=address, value=value, compare=compare)
