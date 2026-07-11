# Кооператив Юг - Finance Lab

Read-only portfolio cashflow and bond analytics engine for T-Invest portfolios.

Finance Lab is the technical core for the «Кооператив Юг» media direction: an engineering view of money and capital.
The project focuses on future cashflows, important dates, data sources, uncertainty, and explainable analytics rather
than trading automation.

## What It Does

- Reads T-Invest portfolio data through a read-only token.
- Tracks bond positions, coupons, amortizations, maturities, offers/calls, and buybacks.
- Builds monthly portfolio cashflow from fixed coupons, floating coupons, dividends, amortizations, and maturities.
- Marks confirmed and estimated values in the terminal output.
- Converts foreign-currency payments into the report currency for monthly totals.
- Stores local SQLite snapshots when explicitly running snapshot commands.

## What It Does Not Do

- It is not an investment advisor.
- It is not a trading robot.
- It does not place, modify, or cancel orders.
- It does not request trading permissions.
- It does not guarantee future payments or forecast accuracy.

## Disclaimer

This software is for personal analytics, research, and educational content workflows. It is not an investment
recommendation. Forecasts, scenarios, and estimated payments are assumptions, not facts. Data should be checked against
broker, issuer, exchange, and regulator sources before making financial decisions. You are responsible for your own
investment decisions.

## Privacy

- The token is read from local `.env` and is not saved to SQLite.
- Use a read-only T-Invest token.
- Do not publish terminal output or reports that include real account IDs, positions, quantities, or average purchase
  prices unless you intend to disclose them.
- `.env`, local SQLite databases, virtual environments, caches, and external API samples are excluded by `.gitignore`.

## Current Status

The current public CLI command is:

```bash
south-invest
```

The legacy command is still available for compatibility:

```bash
t-invest-bonds
```

Legacy module commands such as `python -m app.cli cashflow` and old aliases such as `south-invest portfolio-all` still
work during migration, but new examples use the canonical `south-invest` command tree.

JSON/CSV export is available for cashflow, and `south-invest report` can generate a local report package with
machine-readable files, SVG charts, and an offline HTML report.

The current release target is `0.1.0`, a public alpha focused on the local CLI, demo report package, read-only T-Invest
analytics, and publication-safe anonymized reports. See `CHANGELOG.md` for release notes.

## Try Without A Broker Account

Run a deterministic offline demo without `.env`, a broker token, or network access:

```bash
south-invest demo cashflow --months 12
```

Machine-readable demo output:

```bash
south-invest demo cashflow --months 12 --format json
south-invest demo cashflow --months 12 --format csv --output demo-cashflow/
```

Complete demo report package:

```bash
south-invest demo report --months 12 --output demo-report/
```

The demo portfolio is synthetic and educational. It includes fixed coupons, a floating coupon estimate, a dividend,
amortization, maturity, and a foreign-currency payment converted into RUB. It is not an investment recommendation.

Suggested GitHub repository topics:

```text
bonds
portfolio
cashflow
fixed-income
t-invest
python
financial-analytics
investment-tools
```

## Install

The T-Invest SDK is published on T-Bank's package index. Use it as an extra index when installing:

```bash
python3.12 -m pip install -e ".[dev]" --extra-index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

Create `backend/.env` with:

```bash
INVEST_TOKEN=your_read_only_token
```

## Release Checks

Before publishing a release, run the local quality and smoke checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy .
python scripts/check_no_secrets.py
south-invest demo cashflow --months 12
south-invest demo cashflow --months 12 --format json
south-invest demo cashflow --months 12 --format csv --output demo-cashflow-smoke/
south-invest demo report --months 12 --output demo-report-smoke/
```

If a read-only T-Invest token is available, also verify the real report path:

```bash
south-invest report --months 12 --output report-real/ --anonymize
```

Generated report directories and local runtime data are ignored by git.

## Run

```bash
south-invest
```

Useful options:

```bash
south-invest --db-path invest.db --lookahead-days 730 --as-of 27.04.2026
south-invest --account-id YOUR_ACCOUNT_ID
```

The app only reads accounts, portfolio, instruments, coupons, and bond events. It does not place or cancel orders.

## Run API

The backend also exposes a minimal FastAPI app for the future web frontend.

Local development:

```bash
uvicorn app.api.main:app --reload
```

Initial endpoints:

```text
GET /health
GET /api/v1/demo/dashboard
GET /api/v1/demo/cashflow?months=12
```

Demo API endpoints are deterministic, offline, and do not require `.env`, a broker token, or network access.

## PostgreSQL Foundation

The web API uses PostgreSQL for persisted investment data. Local and Docker environments read the connection string
from `DATABASE_URL`.

Docker development default:

```text
postgresql+psycopg://south_invest:south_invest_dev@db:5432/south_invest
```

Local host default:

```text
postgresql+psycopg://south_invest:south_invest_dev@127.0.0.1:5432/south_invest
```

Run migrations from `invest/backend`:

```bash
alembic upgrade head
```

Or from the repository root with Docker:

```bash
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
```

Do not put real database passwords or broker tokens into committed compose files.

## Full Portfolio Snapshot

Fetch and store the full current portfolio, not only bonds:

```bash
south-invest portfolio snapshot
```

For one account:

```bash
south-invest portfolio snapshot --account-id YOUR_ACCOUNT_ID
```

The command saves data into SQLite tables `portfolio_snapshots` and `portfolio_assets` and prints:

- name
- ISIN
- quantity
- average buy price
- current price

## Monthly Portfolio Cashflow Forecast

Show expected monthly portfolio cashflow from dividends, fixed bond coupons, floating bond coupons, amortizations, and
maturities:

```bash
south-invest cashflow --months 12
```

Optional deterministic start date:

```bash
south-invest cashflow --account-id YOUR_ACCOUNT_ID --months 12 --as-of 27.04.2026
```

The forecast prints one row per month and keeps fixed coupons, floating coupons, dividends, amortizations, and maturities
in separate columns.
It also prints a detailed future payments table for the selected `--months` window.
If `--account-id` is omitted, all accounts are processed.
All monthly totals are shown in the report currency from `--currency` (`RUB` by default). Foreign-currency payments are
converted to RUB using the current T-Invest FX instrument price, while the detailed table keeps the original payment
currency in the `Payment/unit` column.

For floating-rate bonds, future coupon amounts can be estimated from the last known coupon when T-Invest has not
announced the amount yet:

```bash
south-invest cashflow --months 12 --repeat-floating-last-coupon
```

Machine-readable output is available for cashflow:

```bash
south-invest cashflow --months 12 --format json
south-invest cashflow --months 12 --format json --output cashflow.json
south-invest cashflow --months 12 --format csv --output cashflow/
```

CSV directory output creates:

- `cashflow_monthly.csv`
- `cashflow_events.csv`

## Complete Report Package

Generate a local analytics package for a T-Invest portfolio:

```bash
south-invest report --months 12 --output report/
```

For a single account:

```bash
south-invest report --account-id YOUR_ACCOUNT_ID --months 12 --currency RUB --output report/
```

For publication screenshots or content work, hide account IDs and instrument identifiers:

```bash
south-invest report --months 12 --output report/ --anonymize
```

The report command creates:

- `manifest.json`
- `summary.json`
- `portfolio.json` and `portfolio.csv`
- `cashflow_monthly.json` and `cashflow_monthly.csv`
- `cashflow_events.json` and `cashflow_events.csv`
- `maturities.csv`
- `offers.json` and `offers.csv`
- `floating_scenarios.json` and `floating_scenarios.csv`
- `data_quality.json`
- `report.html`
- SVG charts in `charts/`

`report.html` opens locally without a server, external JavaScript, or external fonts. The report package includes
portfolio holdings, cashflow, offers, data quality, and charts. Full floating-rate scenario matrices are still marked as
a report MVP limitation.

Methodology is documented in `docs/methodology.md`. Floating formula and scenario YAML contracts are documented in
`docs/formulas-and-scenarios.md`. Content-agent rules for Telegram, Shorts, and infographic generation are documented in
`docs/content-agent-contract.md`. Future repository organization for web, CLI, and Telegram bot development is captured
in `docs/future-code-organization.md`.

Real account IDs are excluded from machine-readable output by default. Add `--include-account-id` only when you
explicitly want to include them:

```bash
south-invest cashflow --months 12 --format json --include-account-id
```

When maturity payments are found, the command also prints a separate `Maturity details` table with payment date, month,
bond name, ISIN, quantity, amount per bond, and total maturity amount.

When multiple accounts are processed, the command prints a final `All accounts total` table with monthly sums across all
accounts.

## Floating Coupon Forecast

Forecast coupons for floating-rate bonds using announced T-Invest coupons first, then manual YAML formulas plus a selected
rate scenario:

```bash
south-invest floaters forecast --account-id YOUR_ACCOUNT_ID --months 12 --scenario base
```

If `--account-id` is omitted, all accounts are processed:

```bash
south-invest floaters forecast --months 12 --scenario base
```

Optional files:

```bash
south-invest floaters forecast \
  --months 12 \
  --scenario stress \
  --formulas app/data/floating_coupon_formulas.yaml \
  --scenarios app/data/rate_scenarios.yaml
```

Sources in the detailed table:

- `actual`: T-Invest already has the coupon amount for that date.
- `forecast`: coupon was calculated from formula + scenario.
- `unknown`: formula or scenario data is missing; the command does not crash.

The command also prints a monthly summary and a short 12-month total. It is read-only and does not place orders.

## Simple Floating Coupon Scenarios

Approximate floating coupon cashflow without exact formulas. A bond is included only when T-Invest marks it with
`bond.floating_coupon_flag == True`. The command finds the last known coupon payment for each such bond, annualizes it,
then compares three simple scenarios:

- `CURRENT_COUPON`
- `COUPON_MINUS_1_PERCENT`
- `COUPON_PLUS_1_PERCENT`

Run for all accounts:

```bash
south-invest floaters scenarios --months 12
```

Run for one account with detailed rows:

```bash
south-invest floaters scenarios --account-id YOUR_ACCOUNT_ID --months 12 --delta-percent 1.0 --details
```

If a future coupon amount is already announced by T-Invest, the command uses that actual amount in all scenarios. It is
read-only and does not place orders.

## Bond Offer Tracking

Show upcoming bond offers/calls/buybacks/early redemption events for current portfolio bonds:

```bash
south-invest offers --account-id YOUR_ACCOUNT_ID
```

For all accounts:

```bash
south-invest offers --days 180 --warning-days 45
```

The command prints offers sorted by nearest date, marks events inside `--warning-days` as `WARNING`, then prints a small
summary for 30/45/90 day windows and an action-required section for near offers. It is read-only and does not place
orders.

Machine-readable offers output:

```bash
south-invest offers --days 180 --format json
south-invest offers --days 180 --format json --output offers.json
```

Real account IDs are excluded from JSON by default. Use `--include-account-id` only for private reports.
