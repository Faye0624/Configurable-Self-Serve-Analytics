"""Dashboard screen (US13).

Runs the unlock engine, then draws one card per standard analysis:
  * **unlocked** → the template's SQL is run and the result shown as a chart or
    table, with the generated SQL and a CSV download beside it;
  * **locked**   → a greyed card explaining why (the reason from the engine).

A small filter bar drives the KPI breakdown. All SQL and aggregation happen in
``ssa.TemplateEngine``; this view only renders what it returns.
"""

import streamlit as st

import charts
from state import Workspace, get_workspace

# Metric columns the KPI query always returns; anything else in front is the
# grouping dimension.
_KPI_METRICS = {"total", "average", "n"}


def render() -> None:
    ws = get_workspace()
    st.title("Dashboard")

    if not ws.project.tables:
        st.info("Upload and configure data in **Data** — analyses unlock automatically.")
        return

    results = ws.unlock.evaluate(ws.project)  # US9/US10

    # Run KPI once up front so the filter bar knows the available categories.
    kpi_sql, kpi_df, kpi_dim, kpi_error = _run_kpi(ws, results)
    top_n, selected = _filter_bar(kpi_df, kpi_dim)

    st.divider()
    columns = st.columns(3)
    for i, result in enumerate(results):
        with columns[i % 3]:
            with st.container(border=True):
                if not result.unlocked:
                    _locked_card(result)
                elif result.template.name == "KPI":
                    _kpi_card(kpi_sql, kpi_df, kpi_dim, kpi_error, top_n, selected)
                elif result.template.name == "Cohort / retention":
                    _template_card(ws, result, ws.templates.run_cohort, _draw_cohort)
                elif result.template.name == "RFM":
                    _template_card(ws, result, ws.templates.run_rfm, _draw_rfm)


# --------------------------------------------------------------------------- #
# Filter bar (US13: "filterable")
# --------------------------------------------------------------------------- #
def _filter_bar(kpi_df, kpi_dim):
    left, right = st.columns([1, 2])
    top_n = left.slider("Top N (KPI breakdown)", 3, 30, 10)
    selected = []
    if kpi_dim and kpi_df is not None:
        options = kpi_df[kpi_dim].astype(str).tolist()
        selected = right.multiselect(
            f"Filter categories ({kpi_dim})", options,
            help="Leave empty to include all categories.",
        )
    else:
        right.caption("Category filter appears once a KPI breakdown (measure + dimension) is unlocked.")
    return top_n, selected


# --------------------------------------------------------------------------- #
# KPI card
# --------------------------------------------------------------------------- #
def _run_kpi(ws: Workspace, results):
    """Run KPI if unlocked; return (sql, df, dimension_or_None, error_or_None)."""
    if not any(r.unlocked and r.template.name == "KPI" for r in results):
        return None, None, None, None
    try:
        sql, df = ws.templates.run_kpi(ws.project)
    except Exception as exc:  # keep the dashboard rendering if one query fails
        return None, None, None, str(exc)
    dim = next((c for c in df.columns if c not in _KPI_METRICS), None)
    return sql, df, dim, None


def _kpi_card(sql, df, dim, error, top_n, selected):
    st.markdown("**KPI**  🔓")
    if error:
        st.error(error)
        return

    if dim:
        view = df
        if selected:
            view = view[view[dim].astype(str).isin(selected)]
        view = view.nlargest(top_n, "total")
        st.plotly_chart(charts.kpi_bar(view, dim), width="stretch")
    else:
        row = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", f"{row['total']:,.0f}")
        c2.metric("Average", f"{row['average']:,.2f}")
        c3.metric("Rows", f"{int(row['n']):,}")
        st.caption("Assign a **dimension** role to a column to see a breakdown.")

    _sql_and_download(sql, df, "kpi")


# --------------------------------------------------------------------------- #
# Cohort / RFM cards (share the run → draw → SQL/download shape)
# --------------------------------------------------------------------------- #
def _template_card(ws, result, run, draw) -> None:
    st.markdown(f"**{result.template.name}**  🔓")
    try:
        sql, df = run(ws.project)
    except Exception as exc:
        st.error(str(exc))
        return
    draw(df)
    _sql_and_download(sql, df, result.template.name.split()[0].lower())


def _draw_cohort(df) -> None:
    matrix = charts.cohort_matrix(df)
    st.plotly_chart(charts.cohort_heatmap(matrix), width="stretch")
    with st.expander("Retention table"):
        st.dataframe(matrix, width="stretch")


def _draw_rfm(df) -> None:
    st.plotly_chart(charts.rfm_score_bars(df, "r_score"), width="stretch")
    with st.expander("Top entities by monetary value"):
        st.dataframe(df.head(20), width="stretch")


# --------------------------------------------------------------------------- #
# Shared bits
# --------------------------------------------------------------------------- #
def _locked_card(result) -> None:
    st.markdown(f"**{result.template.name}**  🔒")
    st.caption(result.template.description)
    st.warning(result.reason)  # US10: why it's locked


def _sql_and_download(sql: str, df, key: str) -> None:
    """Show the generated SQL and let the result be downloaded (US16/US21 groundwork)."""
    with st.expander("Show SQL"):
        st.code(sql, language="sql")
    st.download_button(
        "Download result (CSV)", df.to_csv(index=False),
        file_name=f"{key}_result.csv", mime="text/csv", key=f"dl_{key}",
    )
