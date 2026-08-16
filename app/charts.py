"""Chart builders for the dashboard.

Pure functions: each takes a DataFrame (as returned by ``TemplateEngine``) and
returns a Plotly figure or a reshaped table. No Streamlit and no analysis logic
here — the SQL/aggregation already happened in ``ssa``; this only presents it.
"""

import pandas as pd
import plotly.express as px

# Single warm hue, matching the app's sand accent, so charts read as one
# product rather than a rainbow.
_BAR_COLOR = "#D9C7A3"
_SEQUENTIAL = [[0, "#241F19"], [0.5, "#8C7F66"], [1, "#F0E4CB"]]  # dark -> sand


def metric_bar(df: pd.DataFrame, dimension: str, value: str = "total"):
    """Bar chart of a measure totalled by a dimension (key metric, grouped)."""
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
    fig = px.imshow(matrix, aspect="auto", color_continuous_scale=_SEQUENTIAL,
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


def rfm_heatmap(df: pd.DataFrame):
    """Classic RFM grid: Recency score (x) × Frequency score (y), each cell
    coloured/labelled by how many customers fall in that R-F combination.
    Top-right = recent & frequent (best); bottom-left = lapsed."""
    grid = (pd.crosstab(df["f_score"], df["r_score"])
            .reindex(index=range(5, 0, -1), columns=range(1, 6))  # F=5 on top
            .fillna(0).astype(int))
    fig = px.imshow(grid, text_auto=True, aspect="auto",
                    color_continuous_scale=_SEQUENTIAL,
                    labels=dict(x="Recency score (R)", y="Frequency score (F)",
                                color="customers"))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(dtick=1)
    return fig
