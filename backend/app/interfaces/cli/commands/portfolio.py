from __future__ import annotations

import argparse

import app.cli as legacy_cli

from app.interfaces.cli.commands._adapter import add_option


def run_snapshot(args: argparse.Namespace) -> int:
    argv = ["portfolio-all"]
    add_option(argv, "--account-id", args.account_id)
    add_option(argv, "--db-path", args.db_path)
    add_option(argv, "--as-of", args.as_of)
    return legacy_cli.main(argv)
