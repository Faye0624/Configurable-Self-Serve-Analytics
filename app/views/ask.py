"""Ask screen — natural-language querying.

Placeholder for now: the NL->SQL engine (US15/US16) is built in Step 10. The
input is disabled so the planned flow is visible without implying it works yet.
"""

import streamlit as st


def render() -> None:
    st.title("Ask")
    st.info(
        "Natural-language querying (NL→SQL) arrives in **Step 10**. You'll type a "
        "question, get the answer and a chart, and see the generated SQL behind "
        "it — which you can copy, download, and re-run without calling the model."
    )
    st.text_input(
        "Ask a question about your data",
        placeholder="e.g. Which product category has the highest total sales?",
        disabled=True,
    )
    st.button("Ask", disabled=True)
