import re
from pathlib import Path

import pandas as pd

from ssa.db import Database
from ssa.models import Column, DatasetTable


# Turn a filename into a safe SQL table name: "Orders 2024.csv" -> "orders_2024".
def _table_name(path: str) -> str:
    stem = Path(path).stem.lower()
    return re.sub(r"\W+", "_", stem).strip("_")


# Loads uploaded CSVs into the database and registers them as DatasetTables.
class DataRegistry:
    def __init__(self, db: Database):
        self._db = db
        self.tables: dict[str, DatasetTable] = {}

    # Read a CSV, store it as a table, and register it.
    def add_csv(self, path: str) -> DatasetTable:
        df = pd.read_csv(path)
        name = _table_name(path)
        self._db.write_dataframe(name, df)

        table = DatasetTable(
            name=name,
            columns=[Column(col, str(df[col].dtype)) for col in df.columns],
            source_file=Path(path).name,
            row_count=len(df),
        )
        self.tables[name] = table
        return table
