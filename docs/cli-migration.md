# CLI Migration

Дата: 2026-07-06

`south-invest` - каноническая публичная команда проекта «Кооператив Юг - Finance Lab».

Старые команды пока сохраняются как совместимость и будут удаляться только после отдельного подтверждения.

## New Command Tree

```bash
south-invest portfolio snapshot
south-invest cashflow
south-invest floaters forecast
south-invest floaters scenarios
south-invest offers
```

## Compatibility Aliases

| Legacy command | New command |
| --- | --- |
| `t-invest-bonds` | `south-invest` |
| `south-invest --db-path invest.db` | `south-invest --db-path invest.db` |
| `python -m app.cli cashflow` | `south-invest cashflow` |
| `python -m app.cli portfolio-all` | `south-invest portfolio snapshot` |
| `python -m app.cli floating-forecast` | `south-invest floaters forecast` |
| `python -m app.cli floating-scenarios` | `south-invest floaters scenarios` |
| `python -m app.cli offers` | `south-invest offers` |

## Current Implementation Note

The new CLI layer lives in `app/interfaces/cli`.

At this migration step, command adapters translate the new command tree to the existing implementations in `app.cli`.
This keeps behavior stable while the application and reporting layers are extracted in later stages.

## Planned Commands

These commands are intentionally not implemented yet:

```bash
south-invest report
south-invest demo report
```

They belong to later roadmap stages: demo portfolio, machine-readable reports, CSV, HTML, and charts.
