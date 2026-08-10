"""Persist and restore the project registry so a project reopens with its data
and semantic configuration intact (addresses the "reconfigure on every restart"
limitation).

Two halves make a project durable:
  * the **data tables** live in the file-backed DuckDB itself, so they survive
    automatically once the database is opened from a file;
  * the **configuration** — table names, column roles, join keys and profiling
    — is saved here as a JSON row in a `_registry` table in that same database,
    and read back on startup to rebuild the domain model.

Loading is defensive: any missing/corrupt registry simply yields None, so the
app starts empty rather than crashing (delete the .duckdb file to reset).
"""

import json

from ssa.db import Database
from ssa.models import Column, DatasetTable, Project, Role

_REGISTRY_TABLE = "_registry"


def save_project(db: Database, project: Project) -> None:
    payload = {
        "name": project.name,
        "tables": [
            {
                "name": t.name,
                "source_file": t.source_file,
                "row_count": t.row_count,
                "columns": [
                    {
                        "name": c.name,
                        "data_type": c.data_type,
                        "role": str(c.role),
                        "is_join_key": c.is_join_key,
                        "key_name": c.key_name,
                        "null_pct": c.null_pct,
                        "distinct_count": c.distinct_count,
                        "sample": c.sample,
                    }
                    for c in t.columns
                ],
            }
            for t in project.tables
        ],
    }
    db.execute(f'CREATE TABLE IF NOT EXISTS "{_REGISTRY_TABLE}" (payload VARCHAR)')
    db.execute(f'DELETE FROM "{_REGISTRY_TABLE}"')
    db.execute(f'INSERT INTO "{_REGISTRY_TABLE}" VALUES (?)',
               [json.dumps(payload, default=str)])


def load_project(db: Database) -> Project | None:
    try:
        rows = db.query(f'SELECT payload FROM "{_REGISTRY_TABLE}"')
    except Exception:
        return None  # registry table doesn't exist yet (fresh database)
    if rows.empty:
        return None
    try:
        data = json.loads(rows.iloc[0]["payload"])
        tables = [
            DatasetTable(
                name=t["name"],
                source_file=t.get("source_file", ""),
                row_count=t.get("row_count", 0),
                columns=[
                    Column(
                        name=c["name"],
                        data_type=c["data_type"],
                        role=Role(c["role"]),
                        is_join_key=c["is_join_key"],
                        key_name=c["key_name"],
                        null_pct=c["null_pct"],
                        distinct_count=c["distinct_count"],
                        sample=c.get("sample", []),
                    )
                    for c in t["columns"]
                ],
            )
            for t in data["tables"]
        ]
        return Project(name=data["name"], tables=tables)
    except Exception:
        return None  # corrupt payload -> start fresh
