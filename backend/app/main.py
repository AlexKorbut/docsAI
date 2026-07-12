from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, family, health, query, reminders
from app.config import get_settings

app = FastAPI(title="docsAI", description="Verified Agentic RAG for family documents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(family.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
