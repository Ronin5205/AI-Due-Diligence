"""
Startup Analyzer CLI.

Usage:
    py -m startup_analyzer.main --init-db
    py -m startup_analyzer.main 830f28bd
    py -m startup_analyzer.main 830f28bd --max-depth 3 --sources hackernews,github
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ANALYZER_DIR = _PROJECT_ROOT / "startup_analyzer"
if str(_ANALYZER_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYZER_DIR))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print("Install dependencies: py -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

load_dotenv(_PROJECT_ROOT / ".env")

from config import load_config  # noqa: E402
from loaders.session_loader import list_sessions, load_session  # noqa: E402
from pipeline.orchestrator import Orchestrator  # noqa: E402
from output.report_builder import write_report  # noqa: E402
from storage.db import init_db, test_connection  # noqa: E402
from storage.database_url import mask_database_url, validate_database_url  # noqa: E402
from storage.repository import Repository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Startup market research analyzer")
    parser.add_argument("session_id", nargs="?", help="Interview session ID to analyze")
    parser.add_argument("--init-db", action="store_true", help="Apply database migrations")
    parser.add_argument("--test-db", action="store_true", help="Test Supabase Postgres connection")
    parser.add_argument("--list-sessions", action="store_true", help="List available sessions")
    parser.add_argument("--max-depth", type=int, default=None, help="Max search depth (default 4)")
    parser.add_argument("--queries-per-source", type=int, default=None, help="Queries per source at depth 0")
    parser.add_argument("--sources", type=str, default=None, help="Comma-separated sources to use")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Keep raw documents and session data in Postgres after analysis (default: flush)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = args.sources.split(",") if args.sources else None
    config = load_config(
        max_depth=args.max_depth,
        queries_per_source=args.queries_per_source,
        sources=sources,
        flush_db_after_run=not args.keep_db,
    )

    if args.test_db or args.init_db:
        if not config.database_url:
            print("DATABASE_URL is not set.", file=sys.stderr)
            print("Set DATABASE_URL or SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD in .env", file=sys.stderr)
            raise SystemExit(1)
        issues = validate_database_url(config.database_url)
        for issue in issues:
            print(f"[db] config issue: {issue}", file=sys.stderr)
        print(f"[db] connecting to {mask_database_url(config.database_url)}", file=sys.stderr)

    if args.test_db:
        test_connection(config.database_url)
        print("Database connection test passed.")
        return

    if args.init_db:
        init_db(config.database_url)
        print("Database migrations applied.")
        if not args.session_id:
            return

    if args.list_sessions:
        sessions = list_sessions()
        if not sessions:
            print("No sessions found in startup_interview/sessions/")
        else:
            for s in sessions:
                print(s)
        return

    if not args.session_id:
        print("Usage: py -m startup_analyzer.main <session_id>", file=sys.stderr)
        print("       py -m startup_analyzer.main --init-db", file=sys.stderr)
        raise SystemExit(1)

    print(f"[analyzer] loading session {args.session_id}...", file=sys.stderr)
    session = load_session(args.session_id)

    orchestrator = Orchestrator(config, session)
    report = orchestrator.run()
    path = write_report(report, output_path=args.output)

    if config.flush_db_after_run:
        repo = Repository(config.database_url)
        deleted = repo.flush_session_data(args.session_id)
        total = sum(deleted.values())
        print(f"[analyzer] flushed {total} DB rows for session {args.session_id}", file=sys.stderr)
        for table, count in deleted.items():
            if count:
                print(f"  {table}: {count}", file=sys.stderr)

    print(f"\nAnalysis complete.")
    print(f"Report written to: {path}")
    print(f"Documents collected: {report.analysis_metadata.documents_collected}")
    print(f"Queries executed: {report.analysis_metadata.queries_executed}")
    print(f"Depth reached: {report.analysis_metadata.depth_reached}")
    print(f"Gemini calls: {report.analysis_metadata.gemini_usage.calls_made}")


if __name__ == "__main__":
    main()
