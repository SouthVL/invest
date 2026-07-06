# Content Agent Contract

This contract explains how a content agent should use a `south-invest report` directory.

The agent must treat the report as analytical source data, not as investment advice.

## Files To Read

Start with these files:

- `manifest.json` - report identity, generation date, data date, mode, scenario, file list, warnings, disclaimer;
- `summary.json` - high-level totals and warnings;
- `cashflow_monthly.json` - monthly cashflow split by payment type;
- `cashflow_events.json` - individual future payment events;
- `offers.json` - offers, calls, buybacks, and early redemption dates;
- `data_quality.json` - source statuses, limitations, anonymization status, and warnings.

Optional files:

- `floating_scenarios.json` - current floating coupon scenario markers;
- `portfolio.json` - portfolio metadata if available;
- `report.html` - human-readable local report;
- `charts/*.svg` - chart assets for cards and video.

## Required Date Citation

Always cite:

- `manifest.as_of` as the data date;
- `manifest.generated_at` as the report generation timestamp;
- `manifest.months` as the forecast window;
- `manifest.currency` as the report currency;
- `manifest.scenario` as the scenario label.

Example:

```text
Данные на 2026-07-01, горизонт расчёта 12 месяцев, валюта отчёта RUB, сценарий base.
```

## Field Meaning

### `summary.json`

- `expected_cashflow` - total expected cashflow in report currency.
- `confirmed_payments` - amount marked as confirmed by source data.
- `forecast_payments` - amount based on scenarios or estimates.
- `unknown_payments_count` - events whose amount is not known.
- `coupons` - fixed plus floating coupon payments.
- `fixed_coupons` - fixed bond coupons.
- `floating_coupons` - floating-rate coupons.
- `dividends` - dividend payments.
- `amortizations` - partial return of bond nominal.
- `maturities` - final return of bond nominal.
- `average_monthly_cashflow` - arithmetic average for the selected window.
- `minimum_month` and `maximum_month` - months with the smallest and largest total cashflow.
- `nearest_offer` - closest offer/call/buyback/early redemption event, if any.
- `attention_events_count` - number of offer events marked as requiring attention.
- `forecast_share` - share of forecast or estimated payments in total cashflow.
- `currency_structure` - original payment currencies when available.
- `warnings` - warnings that must be mentioned if material.

### `cashflow_monthly.json`

Use this file for monthly tables and charts. Each row separates:

- fixed coupons;
- floating coupons;
- dividends;
- amortizations;
- maturities;
- total.

Do not merge amortizations and maturities into income.

### `cashflow_events.json`

Use this file for large future payment lists.

Important fields:

- `payment_date` - event date;
- `payment_type` - `coupon`, `dividend`, `amortization`, or `maturity`;
- `source_status` - data status;
- `source` - source label;
- `is_capital_return` - true for amortization and maturity;
- `payment_total` - original payment currency total when available;
- `total` - report currency total.

### `offers.json`

Offers are not cash payments by themselves.

Important fields:

- `offer_date` - important date;
- `event_type` - `offer`, `put`, `call`, `buyback`, or `unknown`;
- `status` - `ok`, `warning`, or `expired`;
- `days_until_offer` - days from data date to event date.

## Data Status Language

Use these labels carefully:

- `actual` - confirmed by source data;
- `forecast` - calculated from a formula or scenario;
- `estimated` - approximate value;
- `unknown` - not enough data;
- `manual` - entered manually.

When `source_status` is not `actual`, explicitly say that the value is not confirmed.

## What Must Not Be Called Income

Do not call these fields income, yield, profit, or earnings:

- `amortizations`;
- `maturities`;
- events with `is_capital_return: true`.

Use wording such as:

```text
Это возврат части номинала, а не доходность портфеля.
```

Coupons and dividends can be described as payments, but not as guaranteed profit.

## Offer vs Maturity

An offer/call/buyback is an important decision or issuer action date. It is not the same as maturity.

Maturity is final nominal repayment and appears as `payment_type: maturity` in cashflow files.

An offer appears in `offers.json`. It may require attention before maturity, but it should not be counted as a cashflow payment unless a separate payment event exists.

## Amortization Explanation

Amortization is partial nominal repayment before maturity.

Recommended explanation:

```text
Амортизация возвращает часть номинала облигации раньше срока. В cashflow это входящий денежный поток, но это не купонный доход.
```

## Required Warnings

Always mention material warnings from:

- `manifest.warnings`;
- `summary.warnings`;
- `data_quality.warnings`;
- `data_quality.limitations`.

If forecast or estimated payments are present, mention that future payments may change.

If foreign-currency payments are present, mention report currency and original payment currencies.

## Prohibited Output

The content agent must not:

- recommend buying, selling, holding, or avoiding an instrument;
- describe forecasts as guaranteed payments;
- hide forecast or unknown status;
- call capital return income;
- publish account IDs or real instrument identifiers when `data_quality.anonymized` is true;
- infer credit quality or issuer reliability from cashflow alone;
- promise future yield.

## Suggested Content Structure

For a Telegram post:

1. State data date, window, currency, and scenario.
2. Give total expected cashflow and split confirmed vs forecast.
3. Explain the main monthly peak.
4. Separate coupons/dividends from amortization/maturity.
5. Mention nearest offer or attention event.
6. Close with limitations and disclaimer.

For Shorts:

1. Hook: one key number or unusual month.
2. Context: date, window, currency.
3. Breakdown: coupons, dividends, capital return.
4. Risk/uncertainty: actual vs forecast, offers.
5. Closing: not investment advice.

For an infographic:

Use:

- stacked monthly cashflow chart;
- split by payment type;
- marker for nearest offer;
- footnote for data date and forecast status.

## Example Request For A Content Agent

```text
Используй summary.json, cashflow_monthly.json и offers.json.

Подготовь:
1. Telegram-пост до 2500 символов.
2. Сценарий Shorts на 45 секунд.
3. Описание одной инфографики.
4. Три возможных заголовка.

Обязательно:
- укажи дату данных;
- разделяй actual и forecast;
- не называй погашение доходом;
- не давай рекомендаций купить или продать;
- перечисли существенные ограничения расчёта.
```
