import pandas as pd


# Conservative, explainable auto-clean, plus suspicious-value detection.
class CleaningService:
    MISSING_THRESHOLD = 30.0  # percent missing before a column is flagged
    OUTLIER_WHISKER = 1.5     # IQR multiplier for outlier fences

    # Apply safe automatic fixes. Returns the cleaned frame and a log of actions.
    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        df = df.copy()
        actions: list[str] = []

        # Trim whitespace on text values (leave numbers and NaN untouched).
        text_cols = df.select_dtypes(include="object").columns
        for c in text_cols:
            df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
        if len(text_cols):
            actions.append(f"trimmed whitespace on {len(text_cols)} text column(s)")

        # Drop exact-duplicate rows.
        before = len(df)
        df = df.drop_duplicates(ignore_index=True)
        removed = before - len(df)
        if removed:
            actions.append(f"removed {removed} duplicate row(s)")

        return df, actions

    # Point out suspicious columns without changing anything, for the user to
    # confirm / fix / ignore (US4).
    def flag_suspicious(self, df: pd.DataFrame) -> list[str]:
        issues: list[str] = []
        n = len(df)
        for c in df.columns:
            s = df[c]

            null_pct = round(float(s.isna().mean()) * 100, 1) if n else 0.0
            if null_pct >= self.MISSING_THRESHOLD:
                issues.append(f"'{c}': {null_pct}% missing")

            # Object column holding more than one Python type (e.g. numbers + text).
            if s.dtype == object and s.dropna().map(type).nunique() > 1:
                issues.append(f"'{c}': mixed value types")

            # Numeric values far outside the interquartile range.
            if pd.api.types.is_numeric_dtype(s):
                vals = s.dropna()
                if len(vals) >= 4:
                    q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
                    iqr = q3 - q1
                    if iqr > 0:
                        lo = q1 - self.OUTLIER_WHISKER * iqr
                        hi = q3 + self.OUTLIER_WHISKER * iqr
                        n_out = int(((vals < lo) | (vals > hi)).sum())
                        if n_out:
                            issues.append(f"'{c}': {n_out} possible outlier(s)")
        return issues
