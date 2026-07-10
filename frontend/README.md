# Frontend

Next.js frontend for the «Кооператив Юг — Портфель инвестора» web MVP.

The app consumes deterministic demo data and real read-only portfolio data from the backend API:

```text
GET /api/v1/demo/dashboard
POST /api/v1/session/connect
GET /api/v1/portfolio/dashboard
```

## Development

Start backend first:

```bash
cd ../backend
uvicorn app.api.main:app --reload
```

Start frontend:

```bash
npm run dev
```

Default URLs:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`

To point frontend at another backend URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

For containerized production mode, Next.js can use separate API URLs:

```bash
INTERNAL_API_BASE_URL=http://api:8000 NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run start
```

`INTERNAL_API_BASE_URL` is used by server-side Next.js requests. `NEXT_PUBLIC_API_BASE_URL` is used by the browser.

## Quality

```bash
npm run lint
npm run typecheck
npm test
```

## Boundaries

- Do not call T-Invest directly.
- Do not store T-Invest token in browser storage.
- Work with internal backend DTOs only.
- Show period, timestamp, and freshness status for yield and macro data.
- Do not add trading operations or personal buy/sell recommendations.
