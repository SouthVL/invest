# Methodology

This document describes how Cooperative South Finance Lab treats portfolio cashflow data.

## Cashflow Scope

Cashflow is the sum of expected future payments received by the portfolio during the selected report window.

Included event types:

- fixed bond coupons;
- floating bond coupons;
- dividends;
- amortizations;
- maturities.

Amortizations and maturities are capital return. They are included in cashflow totals because money returns to the account, but they are not income or portfolio profit.

## Coupons

Fixed coupons are included when a future coupon payment is available from the data source.

Floating coupons can be:

- confirmed by the source when the source provides a concrete future amount;
- estimated when the user enables a scenario such as repeating the last known coupon;
- unknown when there is no reliable amount and no scenario was requested.

Estimated floating coupons must stay marked as estimates in JSON, CSV, and report summaries.

Formula-based floating coupon forecasts use explicit formula and scenario metadata. Forecasts use only active formulas
whose data quality is not `unknown`. When the exact formula is not known, the event remains `unknown`; the application
must not reuse a similar issue's formula as a substitute. See `docs/formulas-and-scenarios.md`.

## Dividends

Dividends are included when future dividend events are available from the data source. The report does not guarantee that a declared or expected dividend will be paid.

## Amortization And Maturity

Amortization is a partial nominal repayment. Maturity is the final nominal repayment. Both are capital return, not yield.

Reports and charts should keep these values separate from coupons and dividends.

## Currency Conversion

The report currency is RUB by default. When the source returns a payment in another currency and the application has conversion data, the converted amount is stored in report currency while the original payment amount and payment currency remain available on the event.

If conversion data is unavailable, the value must not be silently replaced with zero. It should be marked as unknown or excluded from totals that require a reliable converted amount.

## T-Invest Data

T-Invest mode can use:

- read-only account list;
- current portfolio positions;
- bond coupon events;
- dividend events;
- amortization and maturity events;
- offer, call, buyback, and early redemption events;
- currency data when available.

The application must not place orders, cancel orders, or require a token with trading permissions.

## Manual And Demo Data

Demo mode uses deterministic synthetic data. It does not call T-Invest, does not read `.env`, and does not require network access.

Manual data should be explicitly marked as manual when such inputs are added in later stages.

## Data Status

Each financial value should carry a provenance status:

- `actual` means the value is confirmed by a source;
- `forecast` means the value is calculated by a scenario or formula;
- `estimated` means the value is approximate;
- `unknown` means there is not enough data;
- `manual` means the value was entered by the user.

Current report MVP maps repeated floating coupons to `estimated` and source-provided cashflow events to `actual`.

## Limitations

Forecasts are not investment advice and do not guarantee future payments.

The report is a cashflow view, not a complete portfolio performance report. It does not account for market price changes, taxes, commissions, reinvestment, issuer credit risk, or liquidity risk.
