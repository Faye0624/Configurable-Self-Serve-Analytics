"""Chart builders for the dashboard.

Pure functions: each takes a DataFrame (as returned by ``TemplateEngine``) and
returns a Plotly figure or a reshaped table. No Streamlit and no analysis logic
here — the SQL/aggregation already happened in ``ssa``; this only presents it.
"""

import pandas as pd
import plotly.express as px

# Neutral single-hue palette so the charts read as one product, not a rainbow.
_BAR_COLOR = "#4C6FFF"


def kpi_bar(df: pd.DataFrame, dimension: str, value: str = "total"):
    """Bar chart of a measure totalled by a dimension (KPI, grouped)."""
    fig = px.bar(df, x=dimension, y=value)
    fig.update_traces(marker_color=_BAR_COLOR)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280,
                      xaxis_title=None, yaxis_title=value)
    return fig


def cohort_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape long cohort rows (cohort_month, period, entities) into a matrix."""
    matrix = df.pivot(index="cohort_month", columns="period", values="entities")
    matrix.index = [str(v)[:10] for v in matrix.index]  # trim timestamp to date
    return matrix


def cohort_heatmap(matrix: pd.DataFrame):
    """Heatmap of a cohort retention matrix (rows = cohort, cols = period)."""
    fig = px.imshow(matrix, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(x="months since first activity", y="cohort",
                                color="entities"))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
    return fig


def nl_answer_figure(df: pd.DataFrame):
    """Best-effort chart for an arbitrary NL result.

    If the result is a label column + a numeric column, draw a bar chart;
    otherwise return None and let the caller show the table instead.
    """
    if df is None or df.shape[1] != 2 or len(df) == 0:
        return None
    label, value = df.columns[0], df.columns[1]
    if not pd.api.types.is_numeric_dtype(df[value]) or pd.api.types.is_numeric_dtype(df[label]):
        return None
    top = df.nlargest(min(20, len(df)), value)
    fig = px.bar(top, x=label, y=value)
    fig.update_traces(marker_color=_BAR_COLOR)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, xaxis_title=None)
    return fig


def rfm_score_bars(df: pd.DataFrame, score: str = "r_score"):
    """Bar chart of how many entities fall in each 1-5 score bucket."""
    counts = (df.groupby(score).size().reset_index(name="entities")
              .sort_values(score))
    fig = px.bar(counts, x=score, y="entities")
    fig.update_traces(marker_color=_BAR_COLOR)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280,
                      xaxis_title=f"{score} (1 = low, 5 = high)", yaxis_title="entities")
    fig.update_xaxes(dtick=1)
    return fig
