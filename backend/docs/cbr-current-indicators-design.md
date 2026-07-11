# CBR current indicators design

## Scope

Текущий epic ограничен тремя официальными показателями Банка России:

- key rate;
- latest published RUONIA;
- latest published annual inflation.

Не добавлять валюты, металлы, историю показателей, прогнозы или расчеты купонов в рамках этого epic.

## Sources

Primary public sources:

- `https://www.cbr.ru/hd_base/keyrate/`
- `https://www.cbr.ru/hd_base/ruonia/dynamics/`
- `https://www.cbr.ru/hd_base/infl/`

Discovery on 2026-07-10:

- key rate page exposes an HTML table with columns `Дата` and `Ставка`;
- RUONIA page exposes an HTML table and XLSX link with `Дата ставки`, `Ставка RUONIA`, volume/trades/participants and `Дата публикации`;
- inflation page exposes an HTML table and XLSX link with monthly `Дата`, key rate, annual inflation and target inflation.

## Implementation decision

Initial backend implementation adds:

- domain models independent from CBR HTML;
- application service that supports partial result with warnings;
- `GET /api/v1/macro/current` and `GET /api/v1/macro`;
- isolated CBR integration provider and parser functions.

The current provider uses ordinary HTTP requests and parser isolation.

## Storage and refresh rules

Macro indicators are stored in local SQLite through `MacroIndicatorsRepository`.
The API uses `SOUTH_INVEST_DB_PATH` when it is set; otherwise it writes to `invest.db` in the backend process working directory.

Table:

- `macro_indicator_observations`

The table stores each fetched observation as a separate row. Decimal values are persisted as text, not floats.

Refresh cadence:

- key rate: refresh on or after the 5th day of each month;
- annual inflation YoY: refresh on or after the 5th day of each month;
- RUONIA: refresh once per calendar day.

If refresh is not due, the API returns the latest database value with `quality_status = cached`.
If refresh is due but CBR is unavailable and a database value exists, the API returns that value with `quality_status = stale`.
If no database value exists and CBR fails, the indicator is omitted from the snapshot and a warning is returned.

## Follow-up

- Prefer official XLSX or another machine-readable export if it proves stable.
- Add explicit retention policy for old macro observations.
- Keep tests fixture-based; never assert that example values are forever current.
