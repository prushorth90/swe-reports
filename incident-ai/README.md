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

### Local Ollama assistant

Install and start [Ollama](https://ollama.com), then pull the configured model:

```bash
ollama pull llama3.2:3b
```

When running the backend directly, configure its Ollama connection before starting
Uvicorn:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:3b
```

Docker Compose defaults to `http://host.docker.internal:11434` so its backend
container can reach Ollama on the host. Copy values from `.env.example` into a local
`.env` file to select a different URL or model.

The assistant uses a local RAG pipeline over the Markdown documents in
`backend/data/knowledge/`. On the first question, the backend chunks and embeds the
documents with Ollama, then keeps the vectors in memory for subsequent similarity
searches. The index is rebuilt when the backend restarts; no hosted vector database
or Azure service is used.

Questions about the active incident fields, service metrics, or timeline take the
`simple` route directly to Ollama. Questions that mention historical incidents,
runbooks, troubleshooting, or recommended investigation steps take the `rag` route
through vector retrieval first. Routing uses deterministic phrase and keyword rules;
unmatched questions conservatively use RAG.

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