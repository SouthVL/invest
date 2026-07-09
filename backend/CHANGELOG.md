# Changelog

## 0.1.0

First public alpha release of Kooperativ Yug - Finance Lab.

- Added the canonical `south-invest` CLI command.
- Added deterministic offline demo cashflow and demo report commands.
- Added portfolio report package generation with JSON, CSV, SVG charts, and offline HTML.
- Added monthly cashflow forecasting for fixed coupons, floating coupon estimates, dividends, amortizations, and maturities.
- Added bond offer/call/buyback tracking.
- Added floating coupon forecasts based on versioned YAML formulas and rate scenarios.
- Added anonymized report mode for publication workflows.
- Added local quality checks for tests, Ruff, mypy, smoke commands, and basic secret scanning.

## Notes

- The project is read-only and does not place, modify, or cancel trading orders.
- Forecasts and scenarios are assumptions, not investment recommendations.
- Full floating-rate scenario matrices in the report package are planned after v0.1.
