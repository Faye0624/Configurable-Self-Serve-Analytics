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
    """One fix the user can choose to apply, with evidence of what it affects."""

    key: str          # stable id, e.g. "trim_whitespace"
    label: str        # what it does, in plain words
    detail: str       # how much it would affect ("3 column(s)", "1 row(s)")
    rows: pd.DataFrame | None = None  # the actual offending rows, for review


# Fix identifiers, so UI and service agree without magic strings.
TRIM_WHITESPACE = "trim_whitespace"
DROP_DUPLICATES = "drop_duplicates"


def _text_columns(df: pd.DataFrame) -> list[str]:
    """The columns holding text, whichever pandas version is installed.

    This used to be ``select_dtypes(include="object")``. pandas 3 gives text
    columns a dedicated ``str`` dtype, and a column can also be an explicit
    ``string`` dtype on pandas 2 — in both cases "object" matches nothing, so
    whitespace was silently never found. Ask what the dtype *is* rather than
    naming one.
    """
    return [c for c in df.columns
            if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]


class CleaningService:
    MISSING_THRESHOLD = 30.0  # percent missing before a column is flagged
    OUTLIER_WHISKER = 1.5     # IQR multiplier for outlier fences

    # --- 1. detect: what *could* be cleaned (changes nothing) --------------- #
    # Each option carries the offending rows so the user can see the evidence
    # before deciding, rather than trusting a count.
    MAX_EVIDENCE_ROWS = 50

    def detect(self, df: pd.DataFrame) -> list[CleaningOption]:
        options: list[CleaningOption] = []

        # --- stray whitespace: which rows, in which columns ---------------- #
        text_cols = _text_columns(df)
        padded = pd.DataFrame(
            {c: df[c].map(lambda v: isinstance(v, str) and v != v.strip())
             for c in text_cols},
            index=df.index,
        )
        affected_cols = [c for c in text_cols if padded[c].any()] if len(text_cols) else []
        if affected_cols:
            mask = padded[affected_cols].any(axis=1)
            evidence = df.loc[mask, affected_cols].head(self.MAX_EVIDENCE_ROWS).copy()
            # show the padding explicitly, otherwise it is invisible in a table
            for c in affected_cols:
                evidence[c] = evidence[c].map(
                    lambda v: f"[{v}]" if isinstance(v, str) else v)
            evidence.insert(0, "row", evidence.index)
            n_rows = int(mask.sum())
            options.append(CleaningOption(
                TRIM_WHITESPACE,
                "Extra spaces around text",
                f"{n_rows} {'value' if n_rows == 1 else 'values'} in "
                + ", ".join(affected_cols)
                + " start or end with a space. Spaces are shown as [ ] below.",
                evidence.reset_index(drop=True),
            ))

        # --- exact duplicate rows: show every copy, grouped ---------------- #
        dup_mask = df.duplicated(keep=False)     # keep=False -> flags all copies
        removable = int(df.duplicated().sum())   # how many would actually go
        if removable:
            evidence = df.loc[dup_mask].head(self.MAX_EVIDENCE_ROWS).copy()
            evidence.insert(0, "row", evidence.index)
            options.append(CleaningOption(
                DROP_DUPLICATES,
                "Duplicate rows",
                f"{int(dup_mask.sum())} rows are identical copies. "
                f"Keeping one of each would remove {removable} "
                f"{'row' if removable == 1 else 'rows'}.",
                evidence.reset_index(drop=True),
            ))

        return options

    # --- 2. apply: only the fixes the user approved ------------------------ #
    def apply(self, df: pd.DataFrame, approved: set[str]) -> tuple[pd.DataFrame, list[str]]:
        """Return (frame, log). With nothing approved the frame is unchanged."""
        df = df.copy()
        actions: list[str] = []

        if TRIM_WHITESPACE in approved:
            text_cols = _text_columns(df)
            for c in text_cols:
                df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
            actions.append("removed extra spaces around text values")

        if DROP_DUPLICATES in approved:
            before = len(df)
            df = df.drop_duplicates(ignore_index=True)
            removed = before - len(df)
            if removed:
                actions.append(f"removed {removed} duplicate "
                               f"{'row' if removed == 1 else 'rows'}")

        return df, actions

    # --- 3. flag: problems to review, never auto-fixed (US4) --------------- #
    def flag_suspicious(self, df: pd.DataFrame) -> list[str]:
        issues: list[str] = []
        n = len(df)
        for c in df.columns:
            s = df[c]

            null_pct = round(float(s.isna().mean()) * 100, 1) if n else 0.0
            if null_pct >= self.MISSING_THRESHOLD:
                issues.append(f"{c} — {null_pct}% of values are missing")

            # Object column holding more than one Python type (e.g. numbers + text).
            if s.dtype == object and s.dropna().map(type).nunique() > 1:
                issues.append(f"{c} — mixed data types in the same column")

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
                            issues.append(
                                f"{c} — {n_out} "
                                f"{'value' if n_out == 1 else 'values'} fall far "
                                "outside the typical range (possible outliers)")
        return issues
