"""Ask screen — natural-language querying (US15-US18, US22).

Thin UI over ssa.NLQueryEngine: it takes the question, shows the answer + the
generated SQL (which can be downloaded), surfaces errors for rephrasing, and
lists past queries that can be re-run straight from their saved SQL (no model
call). Before the first question it makes clear what is sent to the model.
"""

import streamlit as st

import charts
from state import Workspace, get_workspace


def render() -> None:
    ws = get_workspace()
    st.title("Ask")

    if not ws.project.tables:
        st.info("Upload and configure data in **Data** first — then ask about it here.")
        return

    st.caption(f"Query backend: **{ws.nl.backend_name}**")
    if not _privacy_gate(ws):
        return

    _ask_form(ws)
    _render_last_result()
    _history(ws)


# US18: tell the user exactly what leaves the machine, and get consent.
def _privacy_gate(ws: Workspace) -> bool:
    with st.expander("What gets sent to the model", expanded=False):
        st.caption("Only the schema below — table and column names, types and roles. "
                   "**No data rows are sent.** With the offline stub, nothing leaves your machine.")
        st.code(ws.nl.schema_prompt(ws.project), language="text")
    consent = st.checkbox(
        "I understand the schema (not the data) may be sent to the language model.",
        key="nl_consent",
    )
    if not consent:
        st.info("Tick the box above to enable questions.")
    return consent


def _ask_form(ws: Workspace) -> None:
    with st.form("nl_ask", clear_on_submit=False):
        question = st.text_input(
            "Ask a question about your data",
            placeholder="e.g. total price by product_category",
        )
        submitted = st.form_submit_button("Ask", type="primary")
    if submitted and question.strip():
        st.session_state.nl_last = ws.nl.ask(ws.project, question.strip())


def _render_last_result() -> None:
    result = st.session_state.get("nl_last")
    if result is None:
        return

    st.divider()
    if result.from_cache:
        st.caption("Re-run from saved SQL — no model call.")
    if result.error:
        st.error(result.error)  # US17: clear message, invite a rephrase
        if result.sql:
            _sql_block(result.sql, "rejected")
        return

    st.markdown(f"**Q:** {result.question}")
    fig = charts.nl_answer_figure(result.data)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    st.dataframe(result.data, width="stretch")
    _sql_block(result.sql, "answer")


# US16: show the generated SQL and let it be downloaded / copied.
def _sql_block(sql: str, key: str) -> None:
    with st.expander("Show generated SQL", expanded=True):
        st.code(sql, language="sql")
        st.download_button("Download SQL", sql, file_name="query.sql",
                           mime="text/sql", key=f"dlsql_{key}")


# US22: replay a past query directly from its stored SQL (skips the model).
def _history(ws: Workspace) -> None:
    if not ws.nl.history:
        return
    st.divider()
    st.markdown("**Query history**")
    st.caption("History stores the generated SQL; re-running executes it directly, without the model.")
    for i, entry in enumerate(ws.nl.history):
        cols = st.columns([6, 1])
        cols[0].write(f"`{entry.when}` — {entry.question}")
        if cols[1].button("Re-run", key=f"rerun_{i}"):
            st.session_state.nl_last = ws.nl.rerun(ws.project, entry.sql, entry.question)
            st.rerun()
