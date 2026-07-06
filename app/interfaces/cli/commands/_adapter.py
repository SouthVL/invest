from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal


def add_option(argv: list[str], name: str, value) -> None:
    if value is None:
        return
    argv.extend([name, format_cli_value(value)])


def add_flag(argv: list[str], name: str, enabled: bool) -> None:
    if enabled:
        argv.append(name)


def format_cli_value(value) -> str:
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def namespace_has(args: argparse.Namespace, name: str) -> bool:
    return hasattr(args, name)
