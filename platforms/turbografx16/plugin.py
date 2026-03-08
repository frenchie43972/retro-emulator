"""TurboGrafx-16 platform plugin entrypoint."""

from emulator.platform import Platform

from .turbografx_platform import TurboGrafx16Platform


class PlatformPlugin:
    def create(self) -> Platform:
        return TurboGrafx16Platform()
