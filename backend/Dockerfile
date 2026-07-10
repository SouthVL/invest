FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md ./
COPY app ./app
COPY invest_bonds ./invest_bonds

RUN python -m pip install . \
    --extra-index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
