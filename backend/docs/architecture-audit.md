# Architecture Audit

Дата аудита: 2026-07-06

Цель документа - зафиксировать текущее состояние репозитория `invest` перед миграцией в аналитическое ядро
«Кооператив Юг - Finance Lab». Код в рамках этапа 0 не менялся.

## 1. Существующие команды

### Установленная CLI-команда

В `pyproject.toml` зарегистрирована одна консольная команда:

```bash
t-invest-bonds
```

Она указывает на `invest_bonds.cli:main`.

Поддерживаемые параметры:

```bash
t-invest-bonds \
  --account-id ACCOUNT_ID \
  --db-path invest.db \
  --lookahead-days 730 \
  --as-of DD.MM.YYYY
```

Назначение: получить облигации из портфеля T-Invest, вывести Rich-таблицу, сохранить снимок в SQLite.

### Модульная CLI-команда

Отдельно используется:

```bash
python -m app.cli
```

Если subcommand не указан, `app.cli` делегирует выполнение в `invest_bonds.cli.main`.

Поддерживаемые subcommands:

```bash
python -m app.cli cashflow
python -m app.cli floating-forecast
python -m app.cli floating-scenarios
python -m app.cli offers
python -m app.cli portfolio-all
```

Назначение команд:

- `cashflow` - общий прогноз портфельного cashflow: фиксированные купоны, флоатеры, дивиденды, амортизации,
  погашения; поддерживает конвертацию в валюту отчёта и флаг `--repeat-floating-last-coupon`.
- `floating-forecast` - прогноз купонов флоатеров через объявленные купоны T-Invest, YAML-формулы и сценарий ставок.
- `floating-scenarios` - упрощённые сценарии флоатеров от последнего известного купона.
- `offers` - поиск ближайших оферт/call/buyback/early redemption по текущим облигациям.
- `portfolio-all` - снимок всего портфеля, не только облигаций, с сохранением в SQLite.

## 2. Команды, использующие старый пакет `invest_bonds`

Непосредственно старый пакет используют:

- `t-invest-bonds` через `invest_bonds.cli:main`.
- `python -m app.cli` без subcommand, потому что `app.cli.main()` вызывает `portfolio_main(argv)` из
  `invest_bonds.cli`.

Также `app.cli` импортирует из `invest_bonds` общие функции и модели:

- `account_title`;
- `select_accounts`;
- `load_settings`;
- `ConfigError`;
- `AccountSummary`;
- `configure_t_invest_sdk`.

Новые интеграционные модули `app/t_invest/*` также используют часть старых утилит:

- `invest_bonds.money`;
- `invest_bonds.adapter._enum_name`;
- `invest_bonds.sdk_compat.configure_t_invest_sdk`.

Вывод: `invest_bonds` пока нельзя удалить без подготовки replacement-слоя.

## 3. Команды, использующие новый пакет `app`

Через `app.cli` работают:

- `cashflow`;
- `floating-forecast`;
- `floating-scenarios`;
- `offers`;
- `portfolio-all`.

Эти команды используют новые доменные модели из `app/domain`, расчёты из `app/analytics`, T-Invest сервисы из
`app/t_invest`, YAML loader из `app/config` и SQLite repository из `app/storage`.

Но `app.cli` остаётся смешанным фасадом: он разбирает аргументы, создаёт T-Invest client, выбирает accounts, вызывает
расчёты, форматирует Rich-таблицы и обрабатывает ошибки в одном файле.

## 4. Дублирующиеся модели

Есть две параллельные модели портфельных/облигационных данных.

### В `invest_bonds.models`

- `AccountSummary`;
- `BondInstrument`;
- `BondPosition`;
- `BondCoupon`;
- `BondEvent`;
- `BondAnalysis`;
- `BondHolding`;
- `BondSnapshot`;
- `Signal`;
- `BondEventType`.

### В `app/domain`

- `PortfolioAsset`;
- `PortfolioSnapshot`;
- `BondPosition`;
- `BondCouponScheduleItem`;
- `CashflowEvent`;
- `MonthlyCashflow`;
- `BondOfferEvent`;
- `FloatingCouponForecastEvent`;
- `FloatingScenarioBondPosition`;
- `FloatingScenarioCouponEvent`;
- `MonthlyFloatingCouponForecast`;
- `MonthlyScenarioForecast`.

Основные пересечения:

- позиция облигации есть в `invest_bonds.models.BondPosition` и `app.domain.bond_position.BondPosition`;
- купонное событие есть в `invest_bonds.models.BondCoupon`, `app.domain.bond_position.BondCouponScheduleItem`,
  `app.domain.cashflow.CashflowEvent` и `app.domain.floating_coupon.FloatingCouponForecastEvent`;
- снимок портфеля есть в `invest_bonds.models.BondSnapshot` и `app.domain.portfolio_all.PortfolioSnapshot`;
- source/status частично разведены: `CashflowSource`, `CouponForecastSource`, `CouponSource`, `OfferStatus`,
  `Signal`.

Проблема: нет единого канонического типа "financial instrument", "position", "payment event", "source status".

## 5. Где бизнес-логика смешана с выводом в терминал

Главная зона смешения - `app/cli.py`.

В одном файле находятся:

- argparse parser;
- функции команд;
- создание `Console`;
- создание T-Invest `Client`;
- чтение `.env`;
- выбор account;
- вызов application/integration сервисов;
- агрегация нескольких account;
- форматирование денежных значений;
- Rich renderers;
- обработка пользовательских ошибок;
- функции `combine_monthly_cashflows` и `combine_portfolio_assets`.

Примеры бизнес-логики внутри CLI:

- `combine_monthly_cashflows`;
- `combine_portfolio_assets`;
- ручная агрегация account-level результатов;
- выбор `to_date` по `--months`;
- частичная нормализация валюты `args.currency.upper()`;
- решение, какие таблицы печатать и когда пропускать пустые результаты.

В `invest_bonds/cli.py` также смешаны:

- argparse;
- создание adapter;
- создание repository;
- вывод Rich-таблиц;
- сохранение snapshot.

## 6. Где код напрямую зависит от T-Invest SDK

Прямые зависимости от T-Invest находятся в:

- `invest_bonds.adapter.TInvestAdapter`;
- `app.cli` - импортирует `Client` внутри каждой команды;
- `app/t_invest/bond_offers.py`;
- `app/t_invest/cashflow.py`;
- `app/t_invest/floating_bonds.py`;
- `app/t_invest/floating_scenarios.py`;
- `app/t_invest/portfolio_all.py`.

Часть SDK-зависимости уже локализована в `app/t_invest`, но `app.cli` всё ещё сам:

- создаёт `Client(settings.invest_token)`;
- вызывает `client.users.get_accounts()`;
- преобразует SDK account в `AccountSummary`.

Также `invest_bonds.sdk_compat.configure_t_invest_sdk()` используется из обоих слоёв.

## 7. Какие расчёты можно запускать без API

Без T-Invest API уже можно запускать чистые расчёты:

- `app.analytics.cashflow_forecast.build_monthly_cashflow`;
- `app.analytics.floating_coupon_forecast.calculate_floating_coupon_per_bond`;
- `app.analytics.floating_coupon_forecast.build_floating_coupon_forecast`;
- `app.analytics.floating_coupon_forecast.aggregate_monthly_floating_forecast`;
- `app.analytics.floating_scenarios.estimate_annual_coupon_rate`;
- `app.analytics.floating_scenarios.build_rate_scenarios`;
- `app.analytics.floating_scenarios.calculate_coupon_payment`;
- `app.analytics.floating_scenarios.build_floating_scenario_forecast`;
- `app.analytics.floating_scenarios.aggregate_monthly_scenarios`;
- `app.analytics.bond_offers.offer_status`;
- `app.analytics.bond_offers.filter_and_sort_offers`;
- `app.analytics.bond_offers.offer_summary_counts`;
- `invest_bonds.rules.analyze_bond`;
- `invest_bonds.rules.nearest_event`;
- `invest_bonds.money` conversion helpers;
- YAML loading from `app.config.floating_coupon_loader`, if local files are present.

CLI-команд без токена и сети пока нет. Demo provider отсутствует.

## 8. Какие сущности уже подходят для JSON-сериализации

Большинство доменных сущностей являются Pydantic `BaseModel` и подходят для JSON-сериализации после выбора политики
для `Decimal`, enum и дат:

- все модели из `app/domain`;
- все модели из `invest_bonds/models.py`;
- `Settings` из `invest_bonds/config.py`.

Ограничения:

- нет стабильной report schema с `schema_version`;
- `Decimal` сейчас не нормализован в единый money object;
- account ID сейчас хранится и выводится напрямую;
- нет общего поля `generated_at`, `as_of`, `data_quality`, `warnings`;
- разные модели используют разные поля статуса: `source`, `status`, `signal`;
- `CashflowEvent.amount_per_bond` исторически называется "per bond", хотя теперь используется и для дивидендов.

## 9. Какие тесты защищают текущее поведение

Текущее покрытие тестами хорошее для расчётных функций и smoke-flow, но ограниченное для end-to-end CLI.

Защищены:

- CLI старого `invest_bonds` с fake adapter: `tests/test_cli.py`;
- Rich renderers и combine helpers из `app.cli`: `tests/test_app_cli.py`;
- monthly cashflow aggregation: `tests/test_cashflow_forecast.py`;
- T-Invest cashflow service для дивидендов и FX на fake client: `tests/test_cashflow_service.py`;
- offer filtering/classification: `tests/test_bond_offers.py`;
- floating coupon forecast: `tests/test_floating_coupon_forecast.py`;
- simplified floating scenarios: `tests/test_floating_scenarios.py`;
- money conversion helpers: `tests/test_money.py`;
- portfolio-all storage/render combine: `tests/test_portfolio_all.py`;
- bond analysis rules: `tests/test_rules.py`;
- SDK warning filter: `tests/test_sdk_compat.py`;
- old SQLite snapshot storage smoke test: `tests/test_storage.py`.

Не защищены или слабо защищены:

- JSON/CSV output, потому что его пока нет;
- demo mode, потому что его пока нет;
- complete `python -m app.cli ...` через argparse с fake T-Invest client;
- GitHub Actions/CI;
- отсутствие токена в traceback/logs;
- публичная anonymization;
- стабильность файлов отчёта.

## 10. Изменения, которые могут сломать обратную совместимость

Рискованные изменения:

- переименование пакета `invest_bonds` или удаление команды `t-invest-bonds`;
- изменение default entry point в `pyproject.toml`;
- изменение формата таблиц Rich, потому что тесты проверяют текстовый вывод;
- переименование полей Pydantic-моделей, особенно `CashflowEvent`, `MonthlyCashflow`, `BondSnapshot`;
- изменение семантики `CashflowSource.ACTUAL`: сейчас fixed coupon определяется как `actual`, а флоатеры могут иметь
  `floating_coupon` или `repeated_floating_coupon`;
- изменение SQLite schemas в `invest_bonds/storage.py` и `app/storage/portfolio_all.py`;
- изменение формата YAML `app/data/floating_coupon_formulas.yaml` и `app/data/rate_scenarios.yaml`;
- перевод валютной конвертации на другой источник курса;
- изменение выбора accounts при отсутствующем `--account-id`;
- удаление вспомогательных функций из `invest_bonds`, которые сейчас импортирует `app`.

Рекомендация: вводить новые команды и модели параллельно, старые команды оставить deprecated wrappers до отдельного
подтверждения.

## 11. Предлагаемая целевая архитектура

Цель - один аналитический engine и одна публичная CLI-команда `south-invest`, без смешения T-Invest, расчётов и Rich.

Предлагаемая структура:

```text
south_invest/
  domain/
    accounts.py
    instruments.py
    positions.py
    cashflow.py
    offers.py
    floating.py
    money.py
    source.py
  application/
    ports.py
    portfolio_service.py
    cashflow_service.py
    floating_service.py
    offers_service.py
    report_service.py
  integrations/
    t_invest/
      client.py
      mapper.py
      portfolio_provider.py
      market_data_provider.py
  infrastructure/
    config.py
    sqlite/
    yaml/
    exports/
  reporting/
    models.py
    serializers/
      json.py
      csv.py
    renderers/
      table.py
      html.py
      svg.py
  interfaces/
    cli/
      main.py
      parser.py
      commands/
      renderers/
  demo/
    provider.py
    fixtures/
```

Минимальные архитектурные правила:

- `domain` не импортирует Rich, argparse, SQLite, `.env`, T-Invest SDK.
- `application` работает через protocol/port interfaces.
- `integrations/t_invest` единственное место, где используется `t_tech.invest`.
- `reporting` получает готовые report models и не пересчитывает финансы.
- `interfaces/cli` только разбирает аргументы, вызывает application service и отдаёт результат renderer.
- account ID и персональные данные маскируются в reporting layer, а не в расчётах.
- source status должен быть единым enum: `actual`, `forecast`, `estimated`, `unknown`, `manual`.

## 12. План миграции без большого одномоментного переписывания

### Шаг 1. Публичное позиционирование и entry point

- Обновить `pyproject.toml`: добавить `south-invest`, metadata, repository URLs, classifiers, keywords.
- Оставить `t-invest-bonds` как deprecated alias.
- Обновить README: read-only, no investment advice, privacy, current commands, migration.

### Шаг 2. Новый CLI-фасад без удаления старого кода

- Добавить новый пакет/модуль CLI, например `app/interfaces/cli` или `south_invest/interfaces/cli`.
- Реализовать `south-invest --help` и subcommands, которые пока делегируют существующим service functions.
- Не переносить всю бизнес-логику сразу.

### Шаг 3. Ввести report models

- Добавить `reporting.models` для `CashflowReport`, `PortfolioReport`, `OffersReport`, `FloatingReport`.
- Начать с cashflow, потому что он уже ближе всего к общей модели будущих выплат.
- Сохранить текущие Rich-таблицы как renderer поверх report model.

### Шаг 4. JSON export

- Добавить `--format table|json` и `--output` минимум для cashflow.
- Ввести `schema_version`, `generated_at`, `as_of`, `report_currency`, `items`, `warnings`, `data_quality`.
- Decimal сериализовать строкой.

### Шаг 5. Demo provider

- Добавить deterministic demo cashflow/portfolio provider без `.env` и сети.
- Использовать те же application services и reporting models.

### Шаг 6. Расширить CSV/report

- После стабилизации JSON добавить CSV.
- Затем `report` command с каталогом артефактов.

### Шаг 7. Постепенно выносить T-Invest и storage

- Перенести account loading из `app.cli` в T-Invest provider.
- Свести `invest_bonds.money` и новые money модели в единый модуль.
- Свести две SQLite repository схемы или явно оставить их как legacy.

### Шаг 8. Удаление legacy только после подтверждения

- После того как `south-invest` покрывает все текущие сценарии и тесты, оставить `t-invest-bonds` deprecated wrapper.
- Удалять `invest_bonds` только отдельным этапом после миграционного периода.

## Основные найденные проблемы

1. Нет единой публичной команды: используется `t-invest-bonds` и `python -m app.cli`.
2. Есть две параллельные модели и две истории развития: `invest_bonds` и `app`.
3. `app/cli.py` слишком крупный и смешивает интерфейс, API, расчёты и rendering.
4. T-Invest SDK частично изолирован, но CLI всё ещё напрямую создаёт client и читает accounts.
5. Нет demo mode без токена.
6. Нет JSON/CSV/report contract.
7. Нет единого source status для всех расчётов.
8. Нет application layer с ports.
9. README описывает текущий CLI, но ещё не позиционирует продукт как «Кооператив Юг - Finance Lab».
10. GitHub CI отсутствует.

## Рекомендуемый следующий этап

Следующий крупный этап по `task.md` - этап 1: публичное название и позиционирование продукта.

Минимальный набор изменений для этапа 1:

- обновить metadata в `pyproject.toml`;
- добавить CLI entry point `south-invest`, пока указывающий на существующий совместимый entry point или новый thin wrapper;
- сохранить `t-invest-bonds`;
- переписать начало README под read-only analytics engine;
- добавить disclaimer и privacy notes;
- дать инструкции по GitHub topics.

Кодовую архитектуру на этапе 1 лучше не трогать, кроме безопасного entry point wrapper.
