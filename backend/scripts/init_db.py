"""Create the schema and load reference data.

Usage:  python scripts/init_db.py [--reset]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.models import Category, Department, RoutingRule, User  # noqa: E402
from app.services.auth import hash_password  # noqa: E402

RESET = "--reset" in sys.argv

if RESET:
    print("Dropping all tables ...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

print("Enabling PostGIS ...")
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

print("Creating tables ...")
Base.metadata.create_all(engine)

print("Adding auth columns ...")
with engine.begin() as conn:
    # users.password_hash and the auth_sessions table are needed for login.
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash text"))
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS auth_sessions ("
            "token varchar(64) PRIMARY KEY, "
            "user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
            "created_at timestamptz NOT NULL DEFAULT now(), "
            "expires_at timestamptz NOT NULL)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires_at "
             "ON auth_sessions (expires_at)")
    )

print("Creating spatial indexes ...")
with engine.begin() as conn:
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_complaints_location_gist "
             "ON complaints USING GIST (location)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_incidents_location_gist "
             "ON incidents USING GIST (location)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_complaints_created_idx "
             "ON complaints (created_at DESC)")
    )

with engine.begin() as conn:
    existing_categories = {row[0] for row in conn.execute(text("SELECT key FROM categories"))}
    for order, cat in enumerate(settings.CATEGORIES):
        if cat["key"] in existing_categories:
            continue
        conn.execute(
            text(
                "INSERT INTO categories (key, name, description, sort_order, active) "
                "VALUES (:k, :n, :d, :s, true)"
            ),
            {"k": cat["key"], "n": cat["name"], "d": cat["description"], "s": order},
        )

    existing_departments = {row[0] for row in conn.execute(text("SELECT key FROM departments"))}
    for dept in settings.DEPARTMENTS:
        if dept["key"] in existing_departments:
            continue
        conn.execute(
            text("INSERT INTO departments (key, name, capacity, active) "
                 "VALUES (:k, :n, :c, true)"),
            {"k": dept["key"], "n": dept["name"], "c": dept["capacity"]},
        )

    existing_rules = {
        row[0]
        for row in conn.execute(text("SELECT category_key FROM routing_rules"))
    }
    for rule in settings.ROUTING_RULES:
        if rule["category"] in existing_rules:
            continue
        conn.execute(
            text(
                "INSERT INTO routing_rules (category_key, priority_band, department_key, "
                "response_hours, priority) VALUES (:c, '*', :d, :h, :p)"
            ),
            {
                "c": rule["category"],
                "d": rule["department"],
                "h": rule["response_hours"],
                "p": 100,
            },
        )

    existing_users = {row[0] for row in conn.execute(text("SELECT username FROM users"))}
    defaults = [
        ("admin", "admin", "Civic Admin", "admin@civicsense.local", "1234"),
        ("reporter", "reporter", "Campus Reporter", "reporter@civicsense.local", "1234"),
        ("citizen", "reporter", "Walk-in Citizen", None, "1234"),
    ]
    for username, role, display, contact, password in defaults:
        if username in existing_users:
            continue
        conn.execute(
            text("INSERT INTO users (username, role, display_name, contact, password_hash, "
                 "created_at) VALUES (:u, :r, :d, :c, :p, now())"),
            {
                "u": username,
                "r": role,
                "d": display,
                "c": contact,
                "p": hash_password(password),
            },
        )

    # Any user that predates the login feature gets the demo password.
    for username, _role, _display, _contact, password in defaults:
        conn.execute(
            text("UPDATE users SET password_hash = :p WHERE username = :u "
                 "AND (password_hash IS NULL OR password_hash = '')"),
            {"u": username, "p": hash_password(password)},
        )

print("Schema ready.")
with engine.begin() as conn:
    for row in conn.execute(
        text("SELECT count(*) FROM complaints")
    ):
        print(f"complaints in db: {row[0]}")
    for row in conn.execute(text("SELECT postgis_version()")):
        print(f"postgis: {row[0]}")
