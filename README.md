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

`frontend/` зарезервирован для будущего web MVP.

Frontend не должен получать или хранить T-Invest token после отправки формы. Все upstream credentials остаются на
backend стороне.

## Repository Files

- `.gitignore` — общие ignore-правила репозитория.
- `LICENSE` — лицензия проекта.
- `backend/README.md` — подробная документация текущего Python backend/CLI.
- `backend/CHANGELOG.md` — история релизов backend/CLI.
