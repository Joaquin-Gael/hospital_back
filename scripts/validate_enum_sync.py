"""CLI to validate that PostgreSQL enums match the application taxonomy."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable

from sqlmodel import Session

from app.audit.enum_utils import AUDIT_ENUM_DEFINITIONS, EnumSyncState, build_sync_plan


def _format_missing(states: Iterable[EnumSyncState]) -> str:
    lines: list[str] = []
    for state in states:
        if not state.missing_labels:
            continue
        lines.append(f"- {state.name}: {', '.join(state.missing_labels)}")
    return "\n".join(lines)


SessionFactory = Callable[[], Session]


def _run_validation(session_factory: SessionFactory) -> list[EnumSyncState]:
    with session_factory() as session:
        return build_sync_plan(session, AUDIT_ENUM_DEFINITIONS)


def main(argv: list[str] | None = None, session_factory_override: SessionFactory | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that PostgreSQL enum types include every taxonomy literal.",
    )
    parser.parse_args(argv)

    if session_factory_override is None:
        from app.db.session import session_factory as session_factory_override

    states = _run_validation(session_factory_override)

    missing = [state for state in states if state.missing_labels]
    if not missing:
        print("All database enum types are synchronized with the application taxonomy.")
        return 0

    print("Missing enum values detected:")
    print(_format_missing(missing))
    print("\nRun `python -m scripts.sync_enums --apply` to add the missing values.")
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
