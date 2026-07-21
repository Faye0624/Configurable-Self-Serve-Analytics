import pandas as pd


# Conservative, explainable auto-clean. Returns the cleaned frame plus a list
# of the actions taken, so the UI can show the user exactly what changed.
class CleaningService:
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
