"""Projects screen — pick or rename the working project.

Multiple isolated projects (US20) is a Could-level feature; for now there is
one workspace, shown here so the navigation matches the planned flow.
"""

import streamlit as st

from state import get_workspace


def render() -> None:
    ws = get_workspace()
    st.title("Projects")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader(ws.project.name)
            st.caption(f"{len(ws.project.tables)} table(s) loaded")
            new_name = st.text_input("Rename project", value=ws.project.name)
            if new_name and new_name != ws.project.name:
                ws.project.name = new_name
                st.rerun()
    with right:
        with st.container(border=True):
            st.subheader("➕ New project")
            st.caption(
                "Multiple isolated projects (US20) is a Could-level feature — "
                "one workspace for now. Use **Data** to upload tables into this project."
            )
