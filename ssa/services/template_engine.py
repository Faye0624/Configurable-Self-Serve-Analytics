"""Analysis templates: generate SQL from the semantic configuration (US11/US12).

A template declares the *roles* it needs; this engine finds columns carrying
those roles and builds the SQL. The roles may live in different tables, in which
case the tables are joined on a declared shared key — so an analysis unlocks and
runs even when the data arrived piece by piece across several uploads.

Every method returns ``(sql, result)`` so the UI can show and download the exact
query behind a number (transparency, US16).

**Join grain.** Joining a table of orders to a table of order lines repeats each
order once per line. Sums stay correct, but counting rows would over-count
events, so when tables are joined the engine counts *distinct join keys*
instead of rows.
"""

from dataclasses import dataclass

import pandas as pd

from ssa.db import Database
from ssa.models import Column, DatasetTable, Project, Role


@dataclass
class _Plan:
    """How to reach a set of roles: a FROM clause plus qualified column names."""

    from_sql: str
    refs: dict[Role, str]          # role -> "table"."column"
    join_key: str | None = None    # qualified join key, set when tables are joined

    @property
    def is_joined(self) -> bool:
        return self.join_key is not None


def _find_role(project: Project, role: Role) -> tuple[DatasetTable | None, Column | None]:
    """First (table, column) carrying the role, else (None, None)."""
    for table in project.tables:
        for column in table.columns:
            if column.role == role:
                return table, column
    return None, None


def _shared_key(left: DatasetTable, right: DatasetTable):
    """The pair of columns joining two tables, if they declare the same key."""
    left_keys = {c.key_name: c for c in left.columns if c.is_join_key}
    for column in right.columns:
        if column.is_join_key and column.key_name in left_keys:
            return left_keys[column.key_name], column
    return None


def _build_plan(project: Project, roles: list[Role]) -> _Plan:
    """Resolve roles to columns and join their tables together if needed."""
    picks: dict[Role, tuple[DatasetTable, Column]] = {}
    for role in roles:
        table, column = _find_role(project, role)
        if column is None:
            raise ValueError(f"this analysis needs a column with the '{role}' role")
        picks[role] = (table, column)

    tables: list[DatasetTable] = []
    for table, _ in picks.values():
        if table not in tables:
            tables.append(table)

    base = tables[0]
    from_sql = f'"{base.name}"'
    joined = [base]
    join_key = None

    for table in tables[1:]:
        pair, left_table = None, None
        for candidate in joined:
            pair = _shared_key(candidate, table)
            if pair:
                left_table = candidate
                break
        if not pair:
            raise ValueError(
                f"'{base.name}' and '{table.name}' hold the columns this analysis "
                "needs but are not connected — declare a shared join key on both"
            )
        left_col, right_col = pair
        left_ref = f'"{left_table.name}"."{left_col.name}"'
        from_sql += (f' JOIN "{table.name}" ON {left_ref} = '
                     f'"{table.name}"."{right_col.name}"')
        joined.append(table)
        join_key = join_key or left_ref

    refs = {role: f'"{t.name}"."{c.name}"' for role, (t, c) in picks.items()}
    return _Plan(from_sql=from_sql, refs=refs, join_key=join_key)


class TemplateEngine:
    def __init__(self, db: Database):
        self._db = db

    # Key metrics: total / average / count of a measure, split by a dimension
    # when one is available and reachable.
    def run_key_metrics(self, project: Project) -> tuple[str, pd.DataFrame]:
        try:                                  # prefer a breakdown by dimension
            plan = _build_plan(project, [Role.MEASURE, Role.DIMENSION])
            dimension = plan.refs[Role.DIMENSION]
        except ValueError:                    # no dimension, or not joinable
            plan = _build_plan(project, [Role.MEASURE])
            dimension = None

        measure = plan.refs[Role.MEASURE]
        if dimension:
            sql = (f'SELECT {dimension} AS "dimension", SUM({measure}) AS total, '
                   f'AVG({measure}) AS average, COUNT(*) AS n '
                   f'FROM {plan.from_sql} GROUP BY {dimension} ORDER BY total DESC')
        else:
            sql = (f'SELECT SUM({measure}) AS total, AVG({measure}) AS average, '
                   f'COUNT(*) AS n FROM {plan.from_sql}')
        result = self._db.query(sql)
        if dimension:                          # name the column after the source
            result = result.rename(columns={"dimension": _column_name(dimension)})
        return sql, result

    # Cohort retention: group entities by the month of their first activity,
    # then count how many are still active N months later.
    def run_cohort(self, project: Project) -> tuple[str, pd.DataFrame]:
        plan = _build_plan(project, [Role.IDENTIFIER, Role.DATE])
        entity, date = plan.refs[Role.IDENTIFIER], plan.refs[Role.DATE]
        sql = (
            f'WITH events AS (\n'
            f'    SELECT {entity} AS entity, CAST({date} AS TIMESTAMP) AS ts\n'
            f'    FROM {plan.from_sql}\n'
            f'),\n'
            f'first_month AS (\n'
            f"    SELECT entity, date_trunc('month', min(ts)) AS cohort_month\n"
            f'    FROM events GROUP BY entity\n'
            f'),\n'
            f'activity AS (\n'
            f'    SELECT f.cohort_month,\n'
            f"           date_diff('month', f.cohort_month, date_trunc('month', e.ts)) AS period,\n"
            f'           e.entity\n'
            f'    FROM events e JOIN first_month f USING (entity)\n'
            f')\n'
            f'SELECT cohort_month, period, count(DISTINCT entity) AS entities\n'
            f'FROM activity GROUP BY cohort_month, period ORDER BY cohort_month, period'
        )
        return sql, self._db.query(sql)

    # RFM: per entity, Recency (days since last activity, measured against the
    # dataset's latest date so it stays reproducible), Frequency (# activities)
    # and Monetary (total), each scored 1-5 with ntile.
    def run_rfm(self, project: Project) -> tuple[str, pd.DataFrame]:
        plan = _build_plan(project, [Role.IDENTIFIER, Role.DATE, Role.MEASURE])
        entity = plan.refs[Role.IDENTIFIER]
        date = plan.refs[Role.DATE]
        amount = plan.refs[Role.MEASURE]

        # Across a join each event repeats per joined row, so count distinct
        # join keys rather than rows.
        event_select = f',\n           {plan.join_key} AS event_id' if plan.is_joined else ""
        frequency = "count(DISTINCT event_id)" if plan.is_joined else "count(*)"

        sql = (
            f'WITH events AS (\n'
            f'    SELECT {entity} AS entity, CAST({date} AS TIMESTAMP) AS ts,\n'
            f'           {amount} AS amount{event_select}\n'
            f'    FROM {plan.from_sql}\n'
            f'),\n'
            f'per_entity AS (\n'
            f'    SELECT entity,\n'
            f"           date_diff('day', max(ts), (SELECT max(ts) FROM events)) AS recency_days,\n"
            f'           {frequency} AS frequency,\n'
            f'           sum(amount) AS monetary\n'
            f'    FROM events GROUP BY entity\n'
            f')\n'
            f'SELECT entity, recency_days, frequency, monetary,\n'
            f'       ntile(5) OVER (ORDER BY recency_days DESC) AS r_score,\n'
            f'       ntile(5) OVER (ORDER BY frequency ASC) AS f_score,\n'
            f'       ntile(5) OVER (ORDER BY monetary ASC) AS m_score\n'
            f'FROM per_entity ORDER BY monetary DESC'
        )
        return sql, self._db.query(sql)


def _column_name(qualified: str) -> str:
    """'"orders"."price"' -> 'price'"""
    return qualified.split(".")[-1].strip('"')
