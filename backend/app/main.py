"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import auth, complaints, tickets

app = FastAPI(
    title="CivicSense API",
    description="AI powered civic intelligence and issue resolution platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(tickets.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_version": config.MODEL_VERSION}
