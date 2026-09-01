"""The analysis cards, locked ones showing what is missing."""

import streamlit as st

import charts
from formatting import pretty_sql
from ssa.models import Role
from ssa.services import columns_for_role
from state import Workspace, get_workspace

# Columns the key-metrics query always returns; anything else in front is the
# grouping dimension.
_METRIC_COLS = {"total", "average", "n"}

# Plain words for the roles, for the picker and the "reading" line on each card.
_METRIC_ROLES = (Role.MEASURE, Role.DIMENSION)

_ROLE_WORDS = {
    Role.MEASURE: "Amount",
    Role.DATE: "Date",
    Role.IDENTIFIER: "Customer",
    Role.DIMENSION: "Category",
}


def render() -> None:
    ws = get_workspace()
    st.title("Dashboard")

    if not ws.project.tables:
        st.info("Upload and configure data in **Data** — analyses unlock automatically.")
        return

    results = ws.unlock.evaluate(ws.project)  # US9/US10

    # Key metrics runs before the cards because the filter bar needs its
    # categories, so its picks are read from state rather than from the widget,
    # which is drawn later inside the card.
    m_chosen = _picks_from_state(ws, "metrics", _METRIC_ROLES)
    m_sql, m_df, m_dim, m_error = _run_key_metrics(ws, results, m_chosen)
    top_n, selected = _filter_bar(m_df, m_dim)

    st.divider()
    columns = st.columns(3)
    for i, result in enumerate(results):
        with columns[i % 3]:
            with st.container(border=True):
                if not result.unlocked:
                    _locked_card(result)
                elif result.template.name == "Key metrics":
                    _metrics_card(ws, m_sql, m_df, m_dim, m_error, top_n, selected)
                elif result.template.name == "Cohort / retention":
                    _template_card(ws, result, ws.templates.run_cohort, _draw_cohort,
                                   "cohort", [Role.IDENTIFIER, Role.DATE])
                elif result.template.name == "RFM":
                    _template_card(ws, result, ws.templates.run_rfm, _draw_rfm,
                                   "rfm", [Role.IDENTIFIER, Role.DATE, Role.MEASURE])

    # Always shown, even when nothing is locked: with only three analyses today
    # an empty board looks finished, and this is what says it is not — more data
    # means more analyses, and there will be more of them to unlock in time.
    st.divider()
    st.caption(
        "You can upload more files whenever you like — the more your data "
        "covers, the more analyses open up."
    )


# --------------------------------------------------------------------------- #
# Which column to read for each role
# --------------------------------------------------------------------------- #
def _card_header(title: str, df, key: str) -> None:
    """The card's title, with the CSV download as an icon on the right.

    The download sat under each chart as a full-width button, which read as
    part of the analysis rather than an action on it.
    """
    left, right = st.columns([5, 1], vertical_alignment="center")
    left.markdown(f"**{title}**")
    if df is not None:
        right.download_button(
            "", df.to_csv(index=False), file_name=f"{key}_result.csv",
            mime="text/csv", key=f"dl_{key}", icon=":material/download:",
            help="Download this result as CSV",
        )


def _pick_key(ws: Workspace, card: str, role: Role) -> str:
    return f"pick_{ws.project.id}_{card}_{role}"


def _column_pickers(ws: Workspace, card: str, roles) -> dict:
    """One dropdown per role, naming the column that card reads it from.

    Always shown, even with a single candidate: a price and a quantity are both
    amounts, and left alone the engine would read whichever came first — a
    choice the user never made and could only discover by reading the SQL.
    Each card picks independently, so one analysis can total revenue while
    another counts units.
    """
    chosen = {}
    for role in roles:
        options = columns_for_role(ws.project, role)
        if options:
            chosen[role] = st.selectbox(_ROLE_WORDS[role], options,
                                        key=_pick_key(ws, card, role))
    return chosen


def _picks_from_state(ws: Workspace, card: str, roles) -> dict:
    """The picks a card's dropdowns already hold, before they are drawn again."""
    return {role: st.session_state[key] for role in roles
            if (key := _pick_key(ws, card, role)) in st.session_state}


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
def _run_key_metrics(ws: Workspace, results, chosen=None):
    """Run key metrics if unlocked; return (sql, df, dimension_or_None, error_or_None)."""
    if not any(r.unlocked and r.template.name == "Key metrics" for r in results):
        return None, None, None, None
    try:
        sql, df = ws.templates.run_key_metrics(ws.project, chosen)
    except Exception as exc:  # keep the dashboard rendering if one query fails
        return None, None, None, str(exc)
    dim = next((c for c in df.columns if c not in _METRIC_COLS), None)
    return sql, df, dim, None


def _metrics_card(ws, sql, df, dim, error, top_n, selected):
    _card_header("Key metrics", df, "metrics")
    _column_pickers(ws, "metrics", _METRIC_ROLES)
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

    _show_sql(sql)


# --------------------------------------------------------------------------- #
# Cohort / RFM cards (share the run → draw → SQL/download shape)
# --------------------------------------------------------------------------- #
def _template_card(ws, result, run, draw, card: str, roles) -> None:
    # The header carries the download, which needs the result — so its place is
    # reserved first and filled once the query has run.
    header = st.container()
    chosen = _column_pickers(ws, card, roles)
    try:
        sql, df = run(ws.project, chosen)
    except Exception as exc:
        with header:
            _card_header(result.template.name, None, card)
        st.error(str(exc))
        return
    with header:
        _card_header(result.template.name, df, card)
    draw(df)
    _show_sql(sql)


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


def _show_sql(sql: str) -> None:
    """The query behind the numbers, always available (US16)."""
    with st.expander("Show SQL"):
        st.code(pretty_sql(sql), language="sql", wrap_lines=True)
