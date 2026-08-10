"""Small display helpers shared by the views."""

import sqlglot


def pretty_sql(sql: str) -> str:
    """Format SQL onto multiple indented lines so it reads top-to-bottom."""
    try:
        return sqlglot.transpile(sql, read="duckdb", pretty=True)[0]
    except Exception:
        return sql
