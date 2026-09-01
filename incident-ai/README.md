# Incident AI

Full-stack starter with a React, TypeScript, and Vite frontend and a FastAPI backend.

## Run locally

### Frontend

```bash
cd incident-ai/frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Backend

From the workspace root:

```bash
cd incident-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

The API is available at http://localhost:8000. Check it with:

```bash
curl http://localhost:8000/health
```

### Docker Compose

```bash
cd incident-ai
docker compose up --build
```

The frontend runs at http://localhost:5173 and the backend at http://localhost:8000.

## Test the backend

With the virtual environment active:

```bash
cd incident-ai/backend
pytest
```