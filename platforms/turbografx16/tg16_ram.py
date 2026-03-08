"""TurboGrafx-16 internal RAM device."""

from emulator.bus import RAM


class TG16RAM(RAM):
    """2KB system RAM region mapped at physical $1F0000-$1F1FFF."""

    def __init__(self) -> None:
        super().__init__(0x2000)
