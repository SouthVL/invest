# Floating Formulas And Rate Scenarios

Floating-rate coupon forecasts depend on two editable data sets:

- `app/data/floating_coupon_formulas.yaml`
- `app/data/rate_scenarios.yaml`

Both files are versioned input data. They should be treated as assumptions, not as confirmed future payments.

## Rate Scenario Fields

Each scenario should include:

- `id` - stable scenario identifier;
- `name` - human-readable name;
- `description` - short explanation;
- `status` - `draft`, `active`, or `archived`;
- `created_at` and `updated_at` - ISO dates;
- `author` - person or organization maintaining the scenario;
- `source.title` and `source.url` - source description;
- `market` or `currency` - scope of the rates;
- `time_range` - modeled period;
- `assumptions` - explicit assumptions;
- `rates` - monthly rates by index.

Example:

```yaml
scenarios:
  base:
    id: cb-key-rate-base-2026-07
    name: Base key-rate scenario
    status: active
    created_at: 2026-07-06
    updated_at: 2026-07-06
    author: Cooperative South
    source:
      title: Manual editorial scenario
      url: null
    market: RU
    currency: RUB
    assumptions:
      - Gradual easing
    rates:
      key_rate:
        2026-07: 18.0
        2026-08: 18.0
```

## Floating Formula Fields

Each formula should include:

- `isin` - exact bond ISIN;
- `name` - instrument name;
- `index` or `base_index` - base rate index;
- `spread_bps` - spread in basis points;
- `day_count` - day count convention;
- `lag_days` - index lag if known;
- `cap_rate_bps` and `floor_rate_bps` - cap/floor if known;
- `source` - source title and optional URL;
- `verified_at` - last verification date;
- `comment` - additional context;
- `status` - `draft`, `active`, or `archived`;
- `data_quality_status` - `verified`, `estimated`, `manual`, or `unknown`.

Forecasts use only formulas with `status: active` and `data_quality_status` other than `unknown`.

If the exact formula is unknown, do not copy a similar issue's formula. Use `data_quality_status: unknown` or omit the formula; the forecast will return `unknown` for future coupons without announced amounts.
