import pandas as pd

from ssa.db import Database
from ssa.models import DatasetTable, Project, Role


# First (table, column) in the project with the given role, else (None, None).
def _first_with_role(project: Project, role: Role):
    for tbl in project.tables:
        for col in tbl.columns:
            if col.role == role:
                return tbl, col
    return None, None


def _dimension_in(table: DatasetTable):
    return next((c for c in table.columns if c.role == Role.DIMENSION), None)


# Generates SQL for the standard templates from the semantic config and runs it
# read-only. Returns (sql, result) so the SQL can be shown and downloaded.
class TemplateEngine:
    def __init__(self, db: Database):
        self._db = db

    # Key metrics: total / average / count of a measure, grouped by a
    # dimension if one exists.
    def run_key_metrics(self, project: Project) -> tuple[str, pd.DataFrame]:
        table, measure = _first_with_role(project, Role.MEASURE)
        if measure is None:
            raise ValueError("Key metrics needs a column with the 'measure' role")

        m, t = measure.name, table.name
        dim = _dimension_in(table)
        if dim:
            sql = (
                f'SELECT "{dim.name}", SUM("{m}") AS total, '
                f'AVG("{m}") AS average, COUNT(*) AS n '
                f'FROM "{t}" GROUP BY "{dim.name}" ORDER BY total DESC'
            )
        else:
            sql = f'SELECT SUM("{m}") AS total, AVG("{m}") AS average, COUNT(*) AS n FROM "{t}"'
        return sql, self._db.query(sql)

    # Cohort retention: group entities by the month of their first activity,
    # then count how many are still active N months later.
    def run_cohort(self, project: Project) -> tuple[str, pd.DataFrame]:
        ti, id_col = _first_with_role(project, Role.IDENTIFIER)
        td, dt_col = _first_with_role(project, Role.DATE)
        if id_col is None or dt_col is None:
            raise ValueError("cohort needs an 'identifier' and a 'date' column")
        if ti is not td:
            raise ValueError("cohort currently needs identifier and date in the same table")

        t, i, d = ti.name, id_col.name, dt_col.name
        sql = (
            f'WITH events AS (\n'
            f'    SELECT "{i}" AS entity, CAST("{d}" AS TIMESTAMP) AS ts FROM "{t}"\n'
            f'),\n'
            f'first_month AS (\n'
            f'    SELECT entity, date_trunc(\'month\', min(ts)) AS cohort_month\n'
            f'    FROM events GROUP BY entity\n'
            f'),\n'
            f'activity AS (\n'
            f'    SELECT f.cohort_month,\n'
            f'           date_diff(\'month\', f.cohort_month, date_trunc(\'month\', e.ts)) AS period,\n'
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
        ti, id_col = _first_with_role(project, Role.IDENTIFIER)
        td, dt_col = _first_with_role(project, Role.DATE)
        tm, me_col = _first_with_role(project, Role.MEASURE)
        if not (id_col and dt_col and me_col):
            raise ValueError("RFM needs 'identifier', 'date' and 'measure' columns")
        if not (ti is td is tm):
            raise ValueError("RFM currently needs identifier, date and measure in the same table")

        t, i, d, m = ti.name, id_col.name, dt_col.name, me_col.name
        sql = (
            f'WITH events AS (\n'
            f'    SELECT "{i}" AS entity, CAST("{d}" AS TIMESTAMP) AS ts, "{m}" AS amount FROM "{t}"\n'
            f'),\n'
            f'per_entity AS (\n'
            f'    SELECT entity,\n'
            f'           date_diff(\'day\', max(ts), (SELECT max(ts) FROM events)) AS recency_days,\n'
            f'           count(*) AS frequency,\n'
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
