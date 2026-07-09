from __future__ import annotations

import argparse

import app.cli as legacy_cli

from app.interfaces.cli.commands._adapter import add_flag, add_option


def run_forecast(args: argparse.Namespace) -> int:
    argv = ["floating-forecast"]
    add_option(argv, "--account-id", args.account_id)
    add_option(argv, "--months", args.months)
    add_option(argv, "--scenario", args.scenario)
    add_option(argv, "--formulas", args.formulas)
    add_option(argv, "--scenarios", args.scenarios)
    add_flag(argv, "--only-unknown", args.only_unknown)
    add_flag(argv, "--details", args.details)
    add_option(argv, "--as-of", args.as_of)
    add_option(argv, "--currency", args.currency)
    return legacy_cli.main(argv)


def run_scenarios(args: argparse.Namespace) -> int:
    argv = ["floating-scenarios"]
    add_option(argv, "--account-id", args.account_id)
    add_option(argv, "--months", args.months)
    add_option(argv, "--delta-percent", args.delta_percent)
    add_flag(argv, "--details", args.details)
    add_option(argv, "--as-of", args.as_of)
    return legacy_cli.main(argv)
