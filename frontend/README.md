# Frontend

Next.js frontend for the «Кооператив Юг — Портфель инвестора» web MVP.

The app currently consumes deterministic demo data from the backend API:

```text
GET /api/v1/demo/dashboard
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
