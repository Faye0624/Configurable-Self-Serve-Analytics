"""The schema contract handed to an NL->SQL model.

Privacy boundary (NFR-2): a Schema carries only *structure* — table names,
column names, data types and semantic roles. It never contains any data rows.
Everything sent to an external model is built from this object, so we can state
exactly what leaves the machine.
"""

from dataclasses import dataclass

from ssa.models import Project, Role

# Map pandas dtypes to SQL-ish types so the model knows how a column is stored
# (e.g. a date kept as TEXT must be CAST before date functions work).
_SQL_TYPES = {"object": "TEXT", "string": "TEXT", "bool": "BOOLEAN",
              "datetime": "TIMESTAMP", "date": "DATE", "int": "BIGINT",
              "float": "DOUBLE"}


def _sql_type(dtype: str) -> str:
    d = dtype.lower()
    return next((sql for key, sql in _SQL_TYPES.items() if key in d), "TEXT")


@dataclass(frozen=True)
class SchemaColumn:
    name: str
    data_type: str
    role: str  # Role value, e.g. "measure"; "unassigned" if not configured


@dataclass(frozen=True)
class SchemaTable:
    name: str
    columns: tuple[SchemaColumn, ...]


@dataclass(frozen=True)
class Schema:
    tables: tuple[SchemaTable, ...]

    def table_names(self) -> set[str]:
        return {t.name for t in self.tables}

    # Human-readable schema string that is sent to the model (no data rows).
    def to_prompt_text(self) -> str:
        lines = []
        for table in self.tables:
            cols = ", ".join(
                f"{c.name} {_sql_type(c.data_type)}"
                + (f" [{c.role}]" if c.role != str(Role.UNASSIGNED) else "")
                for c in table.columns
            )
            lines.append(f"TABLE {table.name}({cols})")
        return "\n".join(lines)


# Build a Schema from a project's configured tables. Reads structure only.
def build_schema(project: Project) -> Schema:
    return Schema(
        tuple(
            SchemaTable(
                table.name,
                tuple(
                    SchemaColumn(col.name, col.data_type, str(col.role))
                    for col in table.columns
                ),
            )
            for table in project.tables
        )
    )
