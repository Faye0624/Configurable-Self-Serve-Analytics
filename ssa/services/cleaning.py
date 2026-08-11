"""Cleaning: propose fixes, apply only what the user approves (US3/US4).

Cleaning is **opt-in**. The service never changes data on its own: it first
*detects* what could be fixed and reports it (how many rows/columns each fix
would affect), and only applies the fixes the user explicitly selects. This
keeps the user in control of their own data — the system explains what it found
and asks, rather than silently rewriting the upload.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CleaningOption:
    """One fix the user can choose to apply."""

    key: str          # stable id, e.g. "trim_whitespace"
    label: str        # what it does, in plain words
    detail: str       # how much it would affect ("3 column(s)", "1 row(s)")


# Fix identifiers, so UI and service agree without magic strings.
TRIM_WHITESPACE = "trim_whitespace"
DROP_DUPLICATES = "drop_duplicates"


class CleaningService:
    MISSING_THRESHOLD = 30.0  # percent missing before a column is flagged
    OUTLIER_WHISKER = 1.5     # IQR multiplier for outlier fences

    # --- 1. detect: what *could* be cleaned (changes nothing) --------------- #
    def detect(self, df: pd.DataFrame) -> list[CleaningOption]:
        options: list[CleaningOption] = []

        text_cols = df.select_dtypes(include="object").columns
        affected = [c for c in text_cols
                    if df[c].map(lambda v: isinstance(v, str) and v != v.strip()).any()]
        if affected:
            options.append(CleaningOption(
                TRIM_WHITESPACE,
                "Trim leading/trailing spaces in text values",
                f"{len(affected)} column(s): " + ", ".join(f"'{c}'" for c in affected),
            ))

        duplicates = int(df.duplicated().sum())
        if duplicates:
            options.append(CleaningOption(
                DROP_DUPLICATES,
                "Remove exact duplicate rows",
                f"{duplicates} row(s)",
            ))

        return options

    # --- 2. apply: only the fixes the user approved ------------------------ #
    def apply(self, df: pd.DataFrame, approved: set[str]) -> tuple[pd.DataFrame, list[str]]:
        """Return (frame, log). With nothing approved the frame is unchanged."""
        df = df.copy()
        actions: list[str] = []

        if TRIM_WHITESPACE in approved:
            text_cols = df.select_dtypes(include="object").columns
            for c in text_cols:
                df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
            actions.append(f"trimmed whitespace on {len(text_cols)} text column(s)")

        if DROP_DUPLICATES in approved:
            before = len(df)
            df = df.drop_duplicates(ignore_index=True)
            removed = before - len(df)
            if removed:
                actions.append(f"removed {removed} duplicate row(s)")

        return df, actions

    # --- 3. flag: problems to review, never auto-fixed (US4) --------------- #
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
