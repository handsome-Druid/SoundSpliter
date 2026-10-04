from typing import NoReturn

from .integration import APP, DI


def main() -> NoReturn:
    APP(DI())()
