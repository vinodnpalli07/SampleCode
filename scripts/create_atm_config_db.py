#!/usr/bin/env python3

"""Create an SQLite database from the ATM config JSON file.

The script normalizes the configuration into relational tables:

* project (single row per configuration)
* devices (one row per device, linked to the project)
* builds (one row per build configuration, linked to the project)
* build_device_tags (mapping table for build tags)
* suppressions (one row per suppressed warning key)
* custom_properties (key/value pairs for the custom section)

Usage:
    python scripts/create_atm_config_db.py --json data/atm_cfg.json --db atm_config.db

Both arguments are optional; the defaults match the paths above.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def parse_bool(value: Any) -> Optional[bool]:
    """Attempt to coerce *value* to a boolean.

    Returns ``None`` when conversion is not possible.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        # Only treat 0/1 style integers as booleans.
        if value in (0, 1):
            return bool(value)
        return None

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False

    return None


def to_int_bool(value: Any) -> Optional[int]:
    """Convert a value to an integer flag (1/0) if it represents a boolean."""

    parsed = parse_bool(value)
    if parsed is None:
        return None
    return int(parsed)


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create the database schema if it does not already exist."""

    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target TEXT NOT NULL,
            project_identifier TEXT,
            systems_pod_exe_env TEXT,
            systems_pod_devboard_build TEXT,
            fa_project TEXT,
            fa_agent TEXT,
            pod_control TEXT,
            cloud_env TEXT,
            cgm_type TEXT,
            do_suppress INTEGER,
            testing_in_bamboo INTEGER
        );

        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            device_type TEXT,
            device_serial TEXT,
            device_tag TEXT,
            FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            build_key TEXT NOT NULL,
            build_dir TEXT,
            buildnum TEXT,
            build_offset INTEGER,
            buildnum_actual TEXT,
            flavor TEXT,
            jobid TEXT,
            FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS build_device_tags (
            build_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (build_id, tag),
            FOREIGN KEY (build_id) REFERENCES builds(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS suppressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            suppression_key TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS custom_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            property_key TEXT NOT NULL,
            property_value TEXT,
            FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
        );
        """
    )


def reset_tables(conn: sqlite3.Connection) -> None:
    """Remove existing rows to ensure idempotent runs."""

    for table in (
        "custom_properties",
        "suppressions",
        "build_device_tags",
        "builds",
        "devices",
        "project",
    ):
        conn.execute(f"DELETE FROM {table};")


def insert_project(conn: sqlite3.Connection, config: Dict[str, Any]) -> int:
    project_info = config.get("project", {})

    cursor = conn.execute(
        """
        INSERT INTO project (
            name,
            target,
            project_identifier,
            systems_pod_exe_env,
            systems_pod_devboard_build,
            fa_project,
            fa_agent,
            pod_control,
            cloud_env,
            cgm_type,
            do_suppress,
            testing_in_bamboo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_info.get("name", ""),
            project_info.get("target", ""),
            project_info.get("id") or None,
            config.get("systems_pod_exe_env"),
            config.get("systems_pod_devboard_build"),
            config.get("fa_project"),
            config.get("fa_agent"),
            config.get("pod_control"),
            config.get("cloud_env"),
            config.get("cgm_type"),
            to_int_bool(config.get("do_suppress")),
            to_int_bool(config.get("testing_in_bamboo")),
        ),
    )
    return cursor.lastrowid


def insert_devices(
    conn: sqlite3.Connection, project_id: int, devices: Iterable[Dict[str, Any]]
) -> None:
    rows = [
        (
            project_id,
            device.get("device_type"),
            device.get("device_serial"),
            device.get("device_tag"),
        )
        for device in devices
    ]

    if rows:
        conn.executemany(
            """
            INSERT INTO devices (
                project_id,
                device_type,
                device_serial,
                device_tag
            ) VALUES (?, ?, ?, ?)
            """,
            rows,
        )


def insert_builds(
    conn: sqlite3.Connection, project_id: int, builds: Iterable[Dict[str, Any]]
) -> None:
    for build in builds:
        cursor = conn.execute(
            """
            INSERT INTO builds (
                project_id,
                build_key,
                build_dir,
                buildnum,
                build_offset,
                buildnum_actual,
                flavor,
                jobid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                build.get("key"),
                build.get("build_dir"),
                build.get("buildnum"),
                build.get("build_offset"),
                build.get("buildnum_actual"),
                build.get("flavor"),
                build.get("jobid"),
            ),
        )

        build_id = cursor.lastrowid
        device_tags = build.get("device_tags") or []
        tag_rows = [(build_id, tag) for tag in device_tags if tag is not None]
        if tag_rows:
            conn.executemany(
                """
                INSERT INTO build_device_tags (build_id, tag) VALUES (?, ?)
                """,
                tag_rows,
            )


def insert_suppressions(
    conn: sqlite3.Connection, project_id: int, suppressions: Iterable[str]
) -> None:
    rows = [
        (project_id, suppression)
        for suppression in suppressions
        if suppression is not None
    ]

    if rows:
        conn.executemany(
            """
            INSERT INTO suppressions (project_id, suppression_key) VALUES (?, ?)
            """,
            rows,
        )


def insert_custom_properties(
    conn: sqlite3.Connection, project_id: int, properties: Dict[str, Any]
) -> None:
    rows = [
        (project_id, key, None if value is None else str(value))
        for key, value in properties.items()
    ]

    if rows:
        conn.executemany(
            """
            INSERT INTO custom_properties (project_id, property_key, property_value)
            VALUES (?, ?, ?)
            """,
            rows,
        )


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON at {path}: {exc}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load the ATM configuration JSON and create an SQLite database."
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("data/atm_cfg.json"),
        help="Path to the ATM configuration JSON file.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("atm_config.db"),
        help="Path to the SQLite database that will be created/updated.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    json_path: Path = args.json
    db_path: Path = args.db

    if not json_path.exists():
        raise SystemExit(f"JSON file not found: {json_path}")

    config = load_json(json_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_tables(conn)
        reset_tables(conn)

        project_id = insert_project(conn, config)
        insert_devices(conn, project_id, config.get("devices", []))
        insert_builds(conn, project_id, config.get("builds", []))
        insert_suppressions(conn, project_id, config.get("suppress", []))
        insert_custom_properties(
            conn, project_id, config.get("custom", {}) or {}
        )

    print(
        "Database created successfully:",
        db_path,
    )


if __name__ == "__main__":
    main()
