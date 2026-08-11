"""Project catalogue and storage (US20 — multiple projects).

Layout:
  * a **catalogue** database holds the accounts (`_users`) and one row per
    project (owner + the saved semantic configuration);
  * each project owns a **separate database file**, `<data_dir>/<project id>.duckdb`,
    holding that project's uploaded tables and its query history.

Giving each project its own file keeps projects fully isolated — two projects can
both have an "orders" table, deleting a project is just dropping its file, and
no SQL anywhere needs to know about namespacing.
"""

import json
from pathlib import Path

from ssa.db import Database
from ssa.models import Column, DatasetTable, Project, Role

_PROJECTS_TABLE = "_projects"


class ProjectStore:
    def __init__(self, catalogue: Database, data_dir: str | Path = "projects"):
        self._db = catalogue
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db.execute(
            f'CREATE TABLE IF NOT EXISTS "{_PROJECTS_TABLE}" '
            "(project_id VARCHAR, owner VARCHAR, name VARCHAR, payload VARCHAR)"
        )

    # --- catalogue --------------------------------------------------------- #
    def list_projects(self, owner: str) -> list[Project]:
        rows = self._db.query(
            f'SELECT payload FROM "{_PROJECTS_TABLE}" WHERE owner = ? ORDER BY name',
            [owner],
        )
        projects = [_deserialise(p) for p in rows["payload"]]
        return [p for p in projects if p is not None]

    def create(self, owner: str, name: str) -> Project:
        project = Project(name=name.strip() or "Untitled project", owner=owner)
        self.save(project)
        return project

    def save(self, project: Project) -> None:
        self._db.execute(
            f'DELETE FROM "{_PROJECTS_TABLE}" WHERE project_id = ?', [project.id]
        )
        self._db.execute(
            f'INSERT INTO "{_PROJECTS_TABLE}" VALUES (?, ?, ?, ?)',
            [project.id, project.owner, project.name, json.dumps(_serialise(project),
                                                                 default=str)],
        )

    def delete(self, project: Project) -> None:
        """Forget the project and remove its data file."""
        self._db.execute(
            f'DELETE FROM "{_PROJECTS_TABLE}" WHERE project_id = ?', [project.id]
        )
        path = self.data_path(project)
        try:
            path.unlink(missing_ok=True)
            path.with_suffix(".duckdb.wal").unlink(missing_ok=True)
        except OSError:
            pass  # a locked/missing file shouldn't block removing the project

    # --- per-project storage ------------------------------------------------ #
    def data_path(self, project: Project) -> Path:
        return self._dir / f"{project.id}.duckdb"

    def open_data_db(self, project: Project) -> Database:
        """The database holding this project's tables and query history."""
        return Database(str(self.data_path(project)))


# --- (de)serialisation of the semantic configuration ------------------------ #
def _serialise(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "owner": project.owner,
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


def _deserialise(payload: str) -> Project | None:
    try:
        data = json.loads(payload)
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
        return Project(name=data["name"], tables=tables,
                       id=data["id"], owner=data.get("owner", ""))
    except Exception:
        return None  # corrupt row -> skip rather than crash
