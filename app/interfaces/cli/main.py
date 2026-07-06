from __future__ import annotations

import sys

from app.interfaces.cli.commands import cashflow, demo, floaters, offers, portfolio
from app.interfaces.cli.parser import build_parser
from invest_bonds.cli import main as legacy_portfolio_main


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("-") and argv[0] not in {"-h", "--help"}):
        return legacy_portfolio_main(argv)

    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)

    if handler == "cashflow":
        return cashflow.run(args)
    if handler == "portfolio_snapshot":
        return portfolio.run_snapshot(args)
    if handler == "floaters_forecast":
        return floaters.run_forecast(args)
    if handler == "floaters_scenarios":
        return floaters.run_scenarios(args)
    if handler == "offers":
        return offers.run(args)
    if handler == "demo_cashflow":
        return demo.run_cashflow(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
