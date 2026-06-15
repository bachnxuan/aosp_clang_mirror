import logging
from logging import Formatter

from rich.console import Console
from rich.logging import RichHandler

LOGGER = logging.getLogger("aosp_clang_mirror")
CONSOLE = Console(color_system="auto")


def _coerce_log_level(level: int | str) -> int:
    if isinstance(level, int):
        return level

    normalized = level.strip().upper()
    resolved = logging.getLevelNamesMapping().get(normalized)
    if isinstance(resolved, int):
        return resolved

    raise ValueError(f"Invalid log level: {level!r}")


def configure_logging(
    *,
    level: int | str = logging.INFO,
) -> None:
    level = _coerce_log_level(level)
    LOGGER.setLevel(level)
    LOGGER.propagate = False

    if LOGGER.handlers:
        for handler in LOGGER.handlers:
            handler.setLevel(level)
        return

    handler = RichHandler(
        console=CONSOLE,
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
    )
    handler.setLevel(level)
    handler.setFormatter(Formatter("%(message)s"))
    LOGGER.addHandler(handler)
