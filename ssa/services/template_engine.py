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

    # KPI: total / average of a measure, grouped by a dimension if one exists.
    def run_kpi(self, project: Project) -> tuple[str, pd.DataFrame]:
        table, measure = _first_with_role(project, Role.MEASURE)
        if measure is None:
            raise ValueError("KPI needs a column with the 'measure' role")

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
