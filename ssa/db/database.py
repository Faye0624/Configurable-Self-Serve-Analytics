import duckdb
import pandas as pd


# Thin wrapper around a DuckDB connection. All SQL goes through here, so the
# storage engine stays swappable (e.g. PostgreSQL in production).
class Database:
    def __init__(self, path: str = ":memory:"):
        self._con = duckdb.connect(path)

    # Run a query and hand back the result as a DataFrame.
    def query(self, sql: str, params: list | None = None) -> pd.DataFrame:
        return self._con.execute(sql, params or []).df()

    # Run a statement that returns no rows (CREATE, INSERT, ...).
    def execute(self, sql: str, params: list | None = None) -> None:
        self._con.execute(sql, params or [])

    # Store a DataFrame as a table, replacing any existing one of that name.
    def write_dataframe(self, table: str, df: pd.DataFrame) -> None:
        self._con.register("_incoming", df)
        self._con.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM _incoming')
        self._con.unregister("_incoming")

    def list_tables(self) -> list[str]:
        return [row[0] for row in self._con.execute("SHOW TABLES").fetchall()]

    def close(self) -> None:
        self._con.close()
