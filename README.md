# T-Invest Bond Tracker

Read-only CLI for tracking bond positions in a T-Invest portfolio.

## Install

The T-Invest SDK is published on T-Bank's package index. Use it as an extra index when installing:

```bash
python3.12 -m pip install -e ".[dev]" --extra-index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

Create `.env` with:

```bash
INVEST_TOKEN=your_read_only_token
```

## Run

```bash
t-invest-bonds
```

Useful options:

```bash
t-invest-bonds --db-path invest.db --lookahead-days 730 --as-of 27.04.2026
t-invest-bonds --account-id YOUR_ACCOUNT_ID
```

The app only reads accounts, portfolio, instruments, coupons, and bond events. It does not place or cancel orders.

## Full Portfolio Snapshot

Fetch and store the full current portfolio, not only bonds:

```bash
python -m app.cli portfolio-all
```

For one account:

```bash
python -m app.cli portfolio-all --account-id YOUR_ACCOUNT_ID
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
python -m app.cli cashflow --months 12
```

Optional deterministic start date:

```bash
python -m app.cli cashflow --account-id YOUR_ACCOUNT_ID --months 12 --as-of 27.04.2026
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
python -m app.cli cashflow --months 12 --repeat-floating-last-coupon
```

When maturity payments are found, the command also prints a separate `Maturity details` table with payment date, month,
bond name, ISIN, quantity, amount per bond, and total maturity amount.

When multiple accounts are processed, the command prints a final `All accounts total` table with monthly sums across all
accounts.

## Floating Coupon Forecast

Forecast coupons for floating-rate bonds using announced T-Invest coupons first, then manual YAML formulas plus a selected
rate scenario:

```bash
python -m app.cli floating-forecast --account-id YOUR_ACCOUNT_ID --months 12 --scenario base
```

If `--account-id` is omitted, all accounts are processed:

```bash
python -m app.cli floating-forecast --months 12 --scenario base
```

Optional files:

```bash
python -m app.cli floating-forecast \
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
python -m app.cli floating-scenarios --months 12
```

Run for one account with detailed rows:

```bash
python -m app.cli floating-scenarios --account-id YOUR_ACCOUNT_ID --months 12 --delta-percent 1.0 --details
```

If a future coupon amount is already announced by T-Invest, the command uses that actual amount in all scenarios. It is
read-only and does not place orders.

## Bond Offer Tracking

Show upcoming bond offers/calls/buybacks/early redemption events for current portfolio bonds:

```bash
python -m app.cli offers --account-id YOUR_ACCOUNT_ID
```

For all accounts:

```bash
python -m app.cli offers --days 180 --warning-days 45
```

The command prints offers sorted by nearest date, marks events inside `--warning-days` as `WARNING`, then prints a small
summary for 30/45/90 day windows and an action-required section for near offers. It is read-only and does not place
orders.
