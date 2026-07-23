"""Streamlit entry point for the Self-Serve Analytics app.

Run locally from the repo root with:
    streamlit run app/main.py

The sidebar routes between four screens — Projects, Data, Dashboard, Ask —
each implemented in ``app/views``. This file only does navigation; every screen
is a thin UI layer over the ``ssa`` services (see ``app/state.py``).
"""

import os
import sys

# Make the app runnable with `streamlit run app/main.py` from the repo root:
# add app/ (for state/views/charts) and the repo root (for the ssa package).
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from state import get_workspace
from views import ask, dashboard, data, projects

# Page-level config must be the first Streamlit call.
st.set_page_config(page_title="Self-Serve Analytics", layout="wide")

# Screen name -> render function.
SCREENS = {
    "Projects": projects.render,
    "Data": data.render,
    "Dashboard": dashboard.render,
    "Ask": ask.render,
}


def render_sidebar() -> str:
    """Draw the left navigation and return the chosen screen."""
    ws = get_workspace()
    st.sidebar.title("Self-Serve Analytics")
    st.sidebar.caption("configurable · transparent · self-hostable")
    st.sidebar.divider()
    st.sidebar.write(f"**Project:** {ws.project.name}")
    st.sidebar.caption(f"{len(ws.project.tables)} table(s) loaded")
    return st.sidebar.radio("Navigate", list(SCREENS), index=1)  # default: Data


def main() -> None:
    SCREENS[render_sidebar()]()


if __name__ == "__main__":
    main()
