"""An offline, deterministic stand-in for a real NL->SQL model.

It covers the common analytic questions with a few transparent rules, so the
whole pipeline (generate -> validate -> execute -> show SQL) is reproducible in
tests and demos without any API key or network. When a real model is
configured it is used instead (see factory.py); this stub is the fallback.

It is intentionally simple and rule-based — the project's technical depth lives
in the SqlGuard and the query engine, not here.
"""

import re

from ssa.llm.base import LLMClient
from ssa.llm.schema import Schema, SchemaTable
from ssa.models import Role

# Aggregation keywords -> SQL function. Longer phrases are checked first.
_AGGREGATIONS = [
    ("average", "AVG"), ("avg", "AVG"), ("mean", "AVG"),
    ("total", "SUM"), ("sum", "SUM"),
    ("how many", "COUNT"), ("number of", "COUNT"), ("count", "COUNT"),
]


class StubLLMClient(LLMClient):
    name = "offline stub"

    def generate_sql(self, question: str, schema: Schema) -> str:
        if not schema.tables:
            raise ValueError("no tables configured")

        q = question.lower()
        table = self._pick_table(q, schema)
        agg = next((fn for kw, fn in _AGGREGATIONS if kw in q), None)

        # Columns are used only when the question actually names them (or via
        # "by <col>"); we don't silently group by a dimension the user didn't ask for.
        measure = self._mentioned(q, table, Role.MEASURE)
        dimension = self._mentioned(q, table, Role.DIMENSION)

        by_match = re.search(r"\bby\s+([a-z0-9_ ]+)", q)
        if by_match:
            col = self._match_column(by_match.group(1), table)
            if col and self._role_of(table, col) == str(Role.MEASURE):
                measure = col            # "... by price" -> price is the measure
            elif col:
                dimension = col          # otherwise "by X" is the grouping column

        # An aggregation needs a measure; fall back to the first one available.
        if agg in ("SUM", "AVG") and measure is None:
            measure = self._first(table, Role.MEASURE)
        # A bare measure question ("total sales") with no verb defaults to a total.
        if agg is None and measure and dimension is None:
            agg = "SUM"

        limit_match = re.search(r"top\s+(\d+)", q)
        limit = int(limit_match.group(1)) if limit_match else None

        sql = self._build(table.name, agg, measure, dimension)
        if limit:
            sql += f" LIMIT {limit}"
        return sql

    # ---- SQL assembly ---------------------------------------------------- #
    def _build(self, table, agg, measure, dimension):
        # Counting rows, optionally per group.
        if agg == "COUNT" or (agg is None and measure is None):
            if dimension:
                return (f'SELECT "{dimension}", COUNT(*) AS n FROM "{table}" '
                        f'GROUP BY "{dimension}" ORDER BY n DESC')
            if agg == "COUNT":
                return f'SELECT COUNT(*) AS n FROM "{table}"'
            return f'SELECT * FROM "{table}" LIMIT 100'  # nothing specific -> preview

        fn = agg or "SUM"
        if dimension:
            return (f'SELECT "{dimension}", {fn}("{measure}") AS value FROM "{table}" '
                    f'GROUP BY "{dimension}" ORDER BY value DESC')
        return f'SELECT {fn}("{measure}") AS value FROM "{table}"'

    # ---- column / table matching ---------------------------------------- #
    def _pick_table(self, q: str, schema: Schema) -> SchemaTable:
        for table in schema.tables:
            if table.name.lower() in q:
                return table
        return schema.tables[0]

    def _mentioned(self, q: str, table: SchemaTable, role: Role):
        """First column of the given role whose name appears in the question."""
        for col in table.columns:
            if col.role == str(role) and col.name.lower() in q:
                return col.name
        return None

    def _first(self, table: SchemaTable, role: Role):
        return next((c.name for c in table.columns if c.role == str(role)), None)

    def _role_of(self, table: SchemaTable, name: str):
        return next((c.role for c in table.columns if c.name == name), None)

    def _match_column(self, text: str, table: SchemaTable):
        text = text.strip()
        for col in table.columns:
            if col.name.lower() in text or text in col.name.lower():
                return col.name
        return None
