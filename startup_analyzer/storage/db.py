"""Supabase Postgres connection helpers."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg

from storage.database_url import mask_database_url

_MIGRATIONS_PATH = Path(__file__).resolve().parent / "migrations.sql"


@contextmanager
def get_connection(database_url: str) -> Generator[psycopg.Connection, None, None]:
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set.\n"
            "Add your Supabase Postgres URI to .env, or set SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD."
        )
    try:
        # Supabase pooler (PgBouncer) does not support prepared statements across
        # pooled connections — required when using parallel DB workers.
        conn = psycopg.connect(
            database_url,
            connect_timeout=15,
            prepare_threshold=None,
        )
    except psycopg.OperationalError as e:
        msg = str(e).lower()
        hint = _connection_hint(msg)
        print(
            f"[db] connection failed: {mask_database_url(database_url)}\n{hint}",
            file=sys.stderr,
        )
        raise RuntimeError(hint) from e
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _connection_hint(error_msg: str) -> str:
    if "password authentication failed" in error_msg:
        return (
            "Password authentication failed.\n"
            "  1. Supabase -> Project Settings -> Database -> Connection string -> URI\n"
            "  2. Use the *database* password (reset under Database Settings if unsure)\n"
            "  3. Do NOT use the anon or service_role API key as the password\n"
            "  4. If the password has special characters (@, #, %, etc.), set instead:\n"
            "       SUPABASE_DB_HOST=db.<project-ref>.supabase.co\n"
            "       SUPABASE_DB_PASSWORD=<your-db-password>\n"
            "     and remove or comment out DATABASE_URL"
        )
    if "timeout" in error_msg:
        return (
            "Connection timed out reaching Supabase Postgres.\n"
            "  1. Confirm the Supabase project is not paused (free tier pauses after inactivity)\n"
            "  2. In Supabase -> Database -> Connection string, try *Session pooler* URI instead of Direct\n"
            "     (host like aws-0-<region>.pooler.supabase.com, user postgres.<project-ref>)\n"
            "  3. Or set SUPABASE_DB_HOST to the pooler host from that URI\n"
            "  4. Check firewall/VPN — port 5432 must be reachable"
        )
    if "could not translate host" in error_msg or "name or service not known" in error_msg:
        return "Hostname could not be resolved. Check SUPABASE_DB_HOST / DATABASE_URL host."
    return f"Database connection error: {error_msg}"


def test_connection(database_url: str) -> None:
    with get_connection(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            row = cur.fetchone()
            print(f"Connected OK: {row[0][:60]}...")


def init_db(database_url: str) -> None:
    sql = _MIGRATIONS_PATH.read_text(encoding="utf-8")
    with get_connection(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
