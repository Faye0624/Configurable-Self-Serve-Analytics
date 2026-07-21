import pandas as pd

from ssa.models import Column


# Fills each column's profiling stats: null %, distinct count, and a few samples.
class ProfilingService:
    SAMPLE_SIZE = 5

    def profile(self, df: pd.DataFrame, columns: list[Column]) -> None:
        n = len(df)
        for col in columns:
            s = df[col.name]
            col.null_pct = round(float(s.isna().mean()) * 100, 1) if n else 0.0
            col.distinct_count = int(s.nunique(dropna=True))
            col.sample = s.dropna().unique()[: self.SAMPLE_SIZE].tolist()
