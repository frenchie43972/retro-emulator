"""NES mapper implementations and factory helpers."""

from .mapper_0_nrom import Mapper0NROM
from .mapper_1_mmc1 import Mapper1MMC1
from .mapper_2_uxrom import Mapper2UxROM
from .mapper_3_cnrom import Mapper3CNROM
from .mapper_base import NESMapper


def create_mapper(mapper_number: int) -> NESMapper:
    mapper_types = {
        0: Mapper0NROM,
        1: Mapper1MMC1,
        2: Mapper2UxROM,
        3: Mapper3CNROM,
    }
    mapper_type = mapper_types.get(mapper_number)
    if mapper_type is None:
        raise ValueError(
            f"Unsupported NES mapper {mapper_number}. Supported mappers: 0 (NROM), 1 (MMC1), 2 (UxROM), 3 (CNROM)."
        )
    return mapper_type()


__all__ = [
    "NESMapper",
    "Mapper0NROM",
    "Mapper1MMC1",
    "Mapper2UxROM",
    "Mapper3CNROM",
    "create_mapper",
]
