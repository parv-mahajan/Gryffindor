"""Runtime configuration: paths, database URL, model identifiers.

Everything that a deployment might want to change lives here. Anything that a
product owner might want to tune (categories, weights, thresholds) lives in
app/settings.py.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"

# A .env file next to the backend package overrides the environment. Missing
# python-dotenv is not an error: the defaults below are enough to run.
try:  # pragma: no cover - depends on the environment
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parent / ".env")
except Exception:  # pragma: no cover
    pass

UPLOAD_DIR = Path(os.getenv("CIVICSENSE_UPLOAD_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Local portable Postgres (this machine). For docker-compose use:
#   postgresql+psycopg://civicsense:civicsense@localhost:5432/civicsense
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres@127.0.0.1:5432/civicsense",
)

EMBEDDING_MODEL = os.getenv("CIVICSENSE_EMBED_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = 384
MODEL_VERSION = os.getenv("CIVICSENSE_MODEL_VERSION", "minilm-l6-v2@2026-10")

# Optional zero-shot image classifier. Off by default; the API degrades to
# text-only scoring when the weights are unavailable.
CLIP_ENABLED = os.getenv("CIVICSENSE_CLIP_ENABLED", "0") == "1"
CLIP_MODEL = os.getenv("CIVICSENSE_CLIP_MODEL", "openai/clip-vit-base-patch32")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CIVICSENSE_CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

# Campus used by the seed data (IIT Bombay, Powai) - keeps the map readable.
CAMPUS_CENTER = (19.0760, 72.8777)
