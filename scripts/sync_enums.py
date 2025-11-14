"""CLI to synchronise PostgreSQL enums with the application taxonomy."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from sqlalchemy import text
from sqlmodel import Session

from app.audit.enum_utils import AUDIT_ENUM_DEFINITIONS, build_sync_plan, missing_statements

SessionFactory = Callable[[], Session]


def main(argv: list[str] | None = None, session_factory_override: SessionFactory | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ensure PostgreSQL enum types include every taxonomy literal.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the ALTER TYPE statements instead of printing them.",
    )
    args = parser.parse_args(argv)

    if session_factory_override is None:
        from app.db.session import session_factory as session_factory_override

    with session_factory_override() as session:
        states = build_sync_plan(session, AUDIT_ENUM_DEFINITIONS)

        statements = missing_statements(states)
        if not statements:
            print("All database enum types are synchronized with the application taxonomy.")
            return 0

        if not args.apply:
            print("Missing enum values detected; run with --apply to execute the fixes.")
            for statement in statements:
                print(statement)
            return 1

        for statement in statements:
            session.exec(text(statement))
        session.commit()

    print(f"Applied {len(statements)} ALTER TYPE statements.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
