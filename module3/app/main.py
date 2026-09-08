from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import findings

app = FastAPI(title="VISTA Module 3 — Adverse Media Screening Engine")

app.include_router(findings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
