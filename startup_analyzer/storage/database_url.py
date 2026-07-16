"""Build and validate Supabase/Postgres connection URLs."""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus, urlparse

_SUPABASE_TAIL = re.compile(
    r"@([\w.-]+\.supabase\.co):(\d+)/(postgres)\b",
    re.IGNORECASE,
)


def _safe_urlparse(url: str):
    try:
        return urlparse(url)
    except ValueError:
        return None


def resolve_database_url() -> str:
    """
    Resolve DATABASE_URL from env, with optional component overrides.

    Prefer SUPABASE_DB_PASSWORD + SUPABASE_DB_HOST when the password has
    special characters that break URL parsing.
    """
    password = os.environ.get("SUPABASE_DB_PASSWORD", "").strip()
    host = os.environ.get("SUPABASE_DB_HOST", "").strip()

    if host and password:
        user = os.environ.get("SUPABASE_DB_USER", "postgres").strip()
        port = os.environ.get("SUPABASE_DB_PORT", "5432").strip()
        dbname = os.environ.get("SUPABASE_DB_NAME", "postgres").strip()
        enc_pass = quote_plus(password)
        url = f"postgresql://{user}:{enc_pass}@{host}:{port}/{dbname}"
    else:
        raw = os.environ.get("DATABASE_URL", "").strip()
        raw = _normalize_database_url(raw)
        url = _extract_supabase_url(raw) or raw

    if not url:
        return ""

    if _has_template_placeholders(url):
        raise RuntimeError(
            "DATABASE_URL still contains template placeholders like [password] or [project].\n"
            "In Supabase: Project Settings -> Database -> Connection string -> URI.\n"
            "Use the database password (reset under Database Settings if needed), not the anon/service API key."
        )

    parsed = _safe_urlparse(url)
    if not parsed or not parsed.hostname:
        raise RuntimeError(
            "DATABASE_URL could not be parsed (missing hostname).\n"
            "This usually means the database password contains '@', '#', or '%'.\n"
            "Fix: comment out DATABASE_URL and set in .env instead:\n"
            "  SUPABASE_DB_HOST=db.<project-ref>.supabase.co\n"
            "  SUPABASE_DB_PASSWORD=<your-database-password>"
        )

    return _ensure_sslmode(url)


def _extract_supabase_url(raw: str) -> str | None:
    """Rebuild URI when password '@' broke urllib parsing (common on Python 3.14+)."""
    if not raw or "supabase.co" not in raw:
        return None

    match = _SUPABASE_TAIL.search(raw)
    if not match:
        return None

    host, port, dbname = match.group(1), match.group(2), match.group(3)
    prefix = raw[: match.start()]
    if "://" not in prefix:
        return None
    creds = prefix.split("://", 1)[-1]
    if ":" not in creds:
        return None
    user, password = creds.split(":", 1)
    enc_pass = quote_plus(password)
    return f"postgresql://{user}:{enc_pass}@{host}:{port}/{dbname}"


def _normalize_database_url(url: str) -> str:
    """Accept bare host or partial URLs and normalize to postgresql URI."""
    if not url:
        return ""
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    if "supabase.co" in url and "://" not in url:
        raise RuntimeError(
            f"DATABASE_URL looks like a hostname only ({url[:40]}...).\n"
            "Use the full URI from Supabase -> Database -> Connection string -> URI,\n"
            "or set SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD separately."
        )
    return url


def _has_template_placeholders(url: str) -> bool:
    return bool(re.search(r"\[(?:password|project|YOUR-PASSWORD)\]", url, re.I))


def _ensure_sslmode(url: str) -> str:
    if "sslmode=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}sslmode=require"


def mask_database_url(url: str) -> str:
    """Return URL safe to print (password redacted)."""
    parsed = _safe_urlparse(url)
    if not parsed or not parsed.hostname:
        extracted = _extract_supabase_url(url)
        if extracted:
            parsed = _safe_urlparse(extracted)
    if not parsed or not parsed.hostname:
        return "postgresql://****"
    host = parsed.hostname
    port = f":{parsed.port}" if parsed.port else ""
    user = parsed.username or "?"
    db = (parsed.path or "/postgres").lstrip("/")
    return f"postgresql://{user}:****@{host}{port}/{db}"


def validate_database_url(url: str) -> list[str]:
    issues: list[str] = []
    if not url:
        issues.append("DATABASE_URL is empty.")
        return issues
    if _has_template_placeholders(url):
        issues.append("URL contains unreplaced [password] or [project] placeholders.")
    parsed = _safe_urlparse(url)
    if not parsed:
        issues.append(
            "URL could not be parsed — password may contain unencoded '@'. "
            "Use SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD instead of DATABASE_URL."
        )
        return issues
    if not parsed.hostname:
        issues.append(
            "URL has no hostname — password may contain unencoded '@' breaking the URI. "
            "Use SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD instead of DATABASE_URL."
        )
    if not parsed.username:
        issues.append("URL has no username.")
    if parsed.password is None and not os.environ.get("SUPABASE_DB_PASSWORD"):
        issues.append("URL has no password segment.")
    return issues
