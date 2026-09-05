from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from researchos.api import datasets, events, experiments, projects, research
from researchos.core.config import settings
from researchos.core.database import init_db
from researchos.core.logging import setup_logging

setup_logging()

app = FastAPI(title="ResearchOS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(research.router)
app.include_router(experiments.router)
app.include_router(events.router)


@app.get("/health")
def health():
    return {"status": "ok"}
