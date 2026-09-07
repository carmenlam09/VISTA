from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import audit, entities, screening, summary
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="VISTA Module 2 — Screening Intelligence Hub", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entities.router)
app.include_router(screening.router)
app.include_router(summary.router)
app.include_router(audit.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    """The API has no UI of its own — the React app in module2/frontend is
    the UI, and this backend is meant to be hit under /api/*. Redirect a
    bare visit to the interactive API docs instead of a bare 404."""
    return RedirectResponse(url="/docs")
