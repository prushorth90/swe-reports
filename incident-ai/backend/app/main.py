from fastapi import FastAPI

from app.api.incidents import router as incidents_router

app = FastAPI(title="Incident AI API")
app.include_router(incidents_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}