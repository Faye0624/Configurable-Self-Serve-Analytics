"""Read-only SQL safety validator (NFR-1).

Every query — whether written by the NL->SQL model or replayed from history —
must pass through here before it touches the database. We parse the SQL into an
abstract syntax tree with sqlglot and enforce, structurally (not by string
matching), that it is a single read-only SELECT over known tables:

  * exactly one statement (no stacked `...; DROP TABLE ...`);
  * the top-level statement is a SELECT or a UNION of SELECTs;
  * no data-/schema-changing node anywhere in the tree
    (INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/COPY/ATTACH/PRAGMA/…);
  * no `SELECT ... INTO` (which writes a table);
  * every referenced table exists in the schema (CTE names excepted).

On any violation it raises SqlGuardError with a human-readable reason, which the
UI shows to the user (US17). It returns the normalised SQL on success.
"""

import sqlglot
from sqlglot import exp


class SqlGuardError(Exception):
    """Raised when a query is not a safe, read-only SELECT."""


# Node types that read-only queries must never contain. Resolved via getattr so
# the list stays valid across sqlglot versions (unknown names are skipped).
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter",
    "TruncateTable", "Copy", "Attach", "Detach", "Pragma", "Command",
    "Set", "Use", "Grant", "Into",
]
_FORBIDDEN = tuple(
    getattr(exp, name) for name in _FORBIDDEN_NAMES if hasattr(exp, name)
)

# Allowed top-level statement types.
_READ_ONLY_TOP = (exp.Select, exp.Union)


class SqlGuard:
    def validate(self, sql: str, allowed_tables: set[str]) -> str:
        try:
            statements = [s for s in sqlglot.parse(sql, dialect="duckdb") if s]
        except Exception as exc:
            raise SqlGuardError(f"could not parse SQL: {exc}") from exc

        if len(statements) != 1:
            raise SqlGuardError("only a single statement is allowed")
        statement = statements[0]

        if not isinstance(statement, _READ_ONLY_TOP):
            kind = type(statement).__name__.upper()
            raise SqlGuardError(f"only read-only SELECT queries are allowed, not {kind}")

        # Defense in depth: reject a forbidden node anywhere (e.g. inside a CTE).
        for node in statement.walk():
            if isinstance(node, _FORBIDDEN):
                raise SqlGuardError(
                    f"'{type(node).__name__}' operations are not allowed (read-only)"
                )

        # Table references must be known. CTE names are local, not real tables.
        cte_names = {cte.alias_or_name for cte in statement.find_all(exp.CTE)}
        for table in statement.find_all(exp.Table):
            if table.name and table.name not in allowed_tables and table.name not in cte_names:
                raise SqlGuardError(f"unknown table '{table.name}'")

        return statement.sql(dialect="duckdb")
