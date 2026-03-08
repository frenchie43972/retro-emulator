"""HuC6280-specific addressing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlockTransferOperands:
    source: int
    destination: int
    length: int


def decode_block_transfer(fetch_u16: callable) -> BlockTransferOperands:
    """Decode HuC6280 block transfer operands from the instruction stream."""

    source = fetch_u16()
    destination = fetch_u16()
    length = fetch_u16()
    if length == 0:
        length = 0x10000
    return BlockTransferOperands(source=source, destination=destination, length=length)
