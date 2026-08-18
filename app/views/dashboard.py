"""Dashboard screen (US13).

Runs the unlock engine, then draws one card per standard analysis:
  * **unlocked** → the template's SQL is run and the result shown as a chart or
    table, with the generated SQL and a CSV download beside it;
  * **locked**   → a greyed card explaining why (the reason from the engine).

A small filter bar drives the key-metrics breakdown. All SQL and aggregation
happen in ``ssa.TemplateEngine``; this view only renders what it returns.
"""

import streamlit as st

import charts
from formatting import pretty_sql
from state import Workspace, get_workspace

# Columns the key-metrics query always returns; anything else in front is the
# grouping dimension.
_METRIC_COLS = {"total", "average", "n"}


def render() -> None:
    ws = get_workspace()
    st.title("Dashboard")

    if not ws.project.tables:
        st.info("Upload and configure data in **Data** — analyses unlock automatically.")
        return

    results = ws.unlock.evaluate(ws.project)  # US9/US10

    # Run key metrics once up front so the filter bar knows the categories.
    m_sql, m_df, m_dim, m_error = _run_key_metrics(ws, results)
    top_n, selected = _filter_bar(m_df, m_dim)

    st.divider()
    columns = st.columns(3)
    for i, result in enumerate(results):
        with columns[i % 3]:
            with st.container(border=True):
                if not result.unlocked:
                    _locked_card(result)
                elif result.template.name == "Key metrics":
                    _metrics_card(m_sql, m_df, m_dim, m_error, top_n, selected)
                elif result.template.name == "Cohort / retention":
                    _template_card(ws, result, ws.templates.run_cohort, _draw_cohort)
                elif result.template.name == "RFM":
                    _template_card(ws, result, ws.templates.run_rfm, _draw_rfm)

    # Always shown, even when nothing is locked: with only three analyses today
    # an empty board looks finished, and this is what says it is not — more data
    # means more analyses, and there will be more of them to unlock in time.
    st.divider()
    st.caption(
        "You can upload more files whenever you like — the more your data "
        "covers, the more analyses open up."
    )


# --------------------------------------------------------------------------- #
# Filter bar (US13: "filterable")
# --------------------------------------------------------------------------- #
def _filter_bar(metric_df, metric_dim):
    left, right = st.columns([1, 2])
    top_n = left.slider("Top N (metric breakdown)", 3, 30, 10)
    selected = []
    if metric_dim and metric_df is not None:
        options = metric_df[metric_dim].astype(str).tolist()
        selected = right.multiselect(
            f"Filter categories ({metric_dim})", options,
            help="Leave empty to include all categories.",
        )
    else:
        right.caption("Category filter appears once a metric breakdown (measure + dimension) is unlocked.")
    return top_n, selected


# --------------------------------------------------------------------------- #
# Key metrics card
# --------------------------------------------------------------------------- #
def _run_key_metrics(ws: Workspace, results):
    """Run key metrics if unlocked; return (sql, df, dimension_or_None, error_or_None)."""
    if not any(r.unlocked and r.template.name == "Key metrics" for r in results):
        return None, None, None, None
    try:
        sql, df = ws.templates.run_key_metrics(ws.project)
    except Exception as exc:  # keep the dashboard rendering if one query fails
        return None, None, None, str(exc)
    dim = next((c for c in df.columns if c not in _METRIC_COLS), None)
    return sql, df, dim, None


def _metrics_card(sql, df, dim, error, top_n, selected):
    st.markdown("**Key metrics**")
    if error:
        st.error(error)
        return

    if dim:
        view = df
        if selected:
            view = view[view[dim].astype(str).isin(selected)]
        view = view.nlargest(top_n, "total")
        st.plotly_chart(charts.metric_bar(view, dim), width="stretch")
    else:
        row = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", f"{row['total']:,.0f}")
        c2.metric("Average", f"{row['average']:,.2f}")
        c3.metric("Rows", f"{int(row['n']):,}")
        st.caption("Assign a **dimension** role to a column to see a breakdown.")

    _sql_and_download(sql, df, "metrics")


# --------------------------------------------------------------------------- #
# Cohort / RFM cards (share the run → draw → SQL/download shape)
# --------------------------------------------------------------------------- #
def _template_card(ws, result, run, draw) -> None:
    st.markdown(f"**{result.template.name}**")
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
    st.plotly_chart(charts.rfm_heatmap(df), width="stretch")
    with st.expander("Top customers by total spend"):
        # Renamed for display only — the query keeps the engine's own column
        # names, which is what Show SQL and the CSV download hand back.
        st.dataframe(df.head(20).rename(columns={"entity": "customer"}),
                     width="stretch")


# --------------------------------------------------------------------------- #
# Shared bits
# --------------------------------------------------------------------------- #
def _locked_card(result) -> None:
    # Only locked cards carry a padlock. Marking the unlocked ones too — with an
    # open padlock — made the two states look alike at a glance, which is exactly
    # the distinction this screen exists to make.
    st.markdown(f"**{result.template.name}**  🔒")
    st.caption(result.template.description)
    st.warning(result.reason)  # US10: why it's locked


def _sql_and_download(sql: str, df, key: str) -> None:
    """Show the generated SQL and let the result be downloaded (US16/US21 groundwork)."""
    with st.expander("Show SQL"):
        st.code(pretty_sql(sql), language="sql", wrap_lines=True)
    st.download_button(
        "Download result (CSV)", df.to_csv(index=False),
        file_name=f"{key}_result.csv", mime="text/csv", key=f"dl_{key}",
    )
