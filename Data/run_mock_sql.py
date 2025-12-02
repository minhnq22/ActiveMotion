#!/usr/bin/env python3
"""Utility script to execute the mock.sql seed file against the SQLite DB."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Optional


def run_sql_script(db_path: Path, sql_path: Path) -> None:
    """Execute the SQL script within a single SQLite transaction."""
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    script = sql_path.read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        conn.executescript(script)
        conn.commit()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the SQLite database using the Data/mock.sql script."
    )
    parser.add_argument(
        "--db",
        default=Path(__file__).with_name("app_data.db"),
        type=Path,
        help="Path to the SQLite database file (default: Data/app_data.db).",
    )
    parser.add_argument(
        "--sql",
        default=Path(__file__).with_name("mock.sql"),
        type=Path,
        help="Path to the SQL script to execute (default: Data/mock.sql).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    run_sql_script(args.db.resolve(), args.sql.resolve())
    print(f"Executed {args.sql} against {args.db}")


if __name__ == "__main__":
    main()

