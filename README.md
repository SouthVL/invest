# South Invest Repository

Репозиторий кода проекта разделён на две рабочие зоны:

```text
invest/
├── backend/
└── frontend/
```

## Backend

`backend/` содержит текущий Python-проект `south-invest`: CLI, аналитическое ядро, T-Invest read-only интеграции,
отчётность, тесты и backend-документацию.

Рабочая директория для существующих команд:

```bash
cd backend
python -m pip install -e ".[dev]" --extra-index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
python -m pytest
python -m ruff check .
python -m mypy .
python scripts/check_no_secrets.py
python -m app.interfaces.cli.main demo report --months 12 --output demo-report-smoke/
```

## Frontend

`frontend/` содержит Next.js web MVP.

Frontend не должен получать или хранить T-Invest token после отправки формы. Все upstream credentials остаются на
backend стороне.

## Docker Compose

Подробная workspace-инструкция: `../doc/development/docker-local-run.md`.

Перед запуском контейнеров останови локальные процессы, которые занимают `3000`, `8000` или `5432`.

Development-режим с hot reload:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Production-like режим:

```bash
docker compose up --build
```

После запуска:

- Frontend: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8000`
- Healthcheck: `http://127.0.0.1:8000/health`
- PostgreSQL: `db:5432` внутри Docker-сети

В обоих режимах frontend использует два адреса API:

- `INTERNAL_API_BASE_URL=http://api:8000` — для server-side запросов Next.js внутри Docker-сети.
- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` — для запросов браузера к опубликованному backend.

Для остановки:

```bash
docker compose -f docker-compose.dev.yml down
docker compose down
```

Применить backend migrations:

```bash
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
```

## Repository Files

- `.gitignore` — общие ignore-правила репозитория.
- `docker-compose.yml` — production-like запуск `db` + `api` + `web`.
- `docker-compose.dev.yml` — development запуск `db` + backend/frontend с hot reload.
- `LICENSE` — лицензия проекта.
- `backend/README.md` — подробная документация текущего Python backend/CLI.
- `backend/CHANGELOG.md` — история релизов backend/CLI.
