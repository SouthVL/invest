# Future Code Organization

This note captures the intended direction for the `invest/` repository after splitting the existing code into
`backend/` and `frontend/`.

## Product Interfaces

The repository may eventually contain three user-facing interfaces:

- Web application/site.
- CLI tool.
- Telegram bot.

They should not become three independent products with duplicated investment logic. The target architecture is one
backend/domain core with several thin interfaces.

```text
T-Invest / Bank of Russia
        |
backend integrations
        |
backend application + domain core
        |
API / CLI / report services
        |
frontend / Telegram bot / terminal user
```

## Target Repository Layout

```text
invest/
├── README.md
├── LICENSE
├── .gitignore
├── backend/
├── frontend/
├── bot/
├── packages/
├── infra/
├── docs/
└── fixtures/
```

## Backend

`backend/` is the center of business logic and data access.

Target layout:

```text
backend/
├── pyproject.toml
├── README.md
├── src/
│   └── south_invest/
│       ├── api/
│       ├── application/
│       ├── domain/
│       ├── integrations/
│       │   ├── tinvest/
│       │   └── cbr/
│       ├── reporting/
│       ├── storage/
│       ├── security/
│       └── settings.py
├── cli/
│   └── south_invest_cli/
├── tests/
└── scripts/
```

Current packages `app/` and `invest_bonds/` should not be rewritten in one large refactor. Move them gradually toward
`src/south_invest/` in small, tested steps:

1. Domain models and money logic.
2. Application services.
3. Integrations.
4. Reporting.
5. CLI compatibility layer.

## CLI

The CLI should remain a thin interface over backend application services:

- parse arguments;
- call application services;
- render terminal, JSON, CSV, HTML, or report package output.

The CLI should not duplicate T-Invest access, cashflow calculations, anonymization, or report logic.

## Frontend

`frontend/` should call only the backend API.

Target layout:

```text
frontend/
├── package.json
├── app/
├── components/
├── features/
│   ├── onboarding/
│   ├── dashboard/
│   ├── positions/
│   └── reports/
├── lib/
├── mocks/
└── tests/
```

Rules:

- Do not call T-Invest directly.
- Do not store T-Invest token in browser storage.
- Work with internal backend DTOs only.
- Always show period, timestamp, and freshness status for yield and macro data.

## Telegram Bot

`bot/` should also call the backend API instead of T-Invest directly.

Target layout:

```text
bot/
├── pyproject.toml
├── src/
│   └── south_invest_bot/
│       ├── handlers/
│       ├── keyboards/
│       ├── messages/
│       └── client.py
└── tests/
```

The bot layer should contain Telegram-specific handlers, texts, keyboards, and backend API client code. It should not
contain investment calculations or upstream credentials.

## Shared Contracts

Use `packages/contracts/` for OpenAPI, generated TypeScript client/types, and JSON schemas.

```text
packages/
└── contracts/
    ├── openapi.json
    ├── schemas/
    └── generated/
```

Frontend and bot clients should be generated from backend contracts when practical.

## Fixtures And Infra

Use `fixtures/` for deterministic demo and upstream-like samples:

```text
fixtures/
├── tinvest/
├── cbr/
└── demo/
```

Use `infra/` for local runtime and deployment support:

```text
infra/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── nginx/
```

## Development Order

1. Stabilize the new `backend/` location.
2. Commit the structural move separately from behavioral changes.
3. Add a FastAPI skeleton with `/health` and demo dashboard endpoints.
4. Add `packages/contracts/` after OpenAPI starts to matter.
5. Build `frontend/` on mock/demo API first.
6. Add real server-session token flow.
7. Add Telegram bot only after backend API and security boundaries are stable.

## Non-Negotiable Boundaries

- No trading operations.
- No order placement, modification, or cancellation.
- No token, authorization header, session secret, or full account id logging.
- No money calculations with `float`.
- No missing data silently replaced with zero.
- No comparisons across non-comparable periods.
