from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Formatter,
    LogRecord,
    StreamHandler,
    basicConfig,
)
from sys import argv
from typing import TextIO, override


class Logger:
    class _Formatter(Formatter):
        @override
        def format(self, record: LogRecord) -> str:
            colors: dict[int, str] = {
                DEBUG: "\033[36m",
                INFO: "\033[32m",
                WARNING: "\033[33m",
                ERROR: "\033[31m",
                CRITICAL: "\033[35m",
            }
            record.levelname = (
                f"{colors.get(record.levelno, '')}{record.levelname}\033[0m"
            )
            return super().format(record)

    def __new__(cls) -> None:
        handler: StreamHandler[TextIO] = StreamHandler()
        handler.setFormatter(
            fmt=cls._Formatter(
                fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
            )
        )
        if "--debug" in argv:
            argv.remove("--debug")
            basicConfig(level=DEBUG, handlers=(handler,))
        else:
            basicConfig(level=INFO, handlers=(handler,))
