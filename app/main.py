"""Streamlit entry point for the Self-Serve Analytics app.

Run locally from the repo root with:
    streamlit run app/main.py

Routing has three levels: sign in, pick a project, then work inside it
(Data / Dashboard / Ask). Every screen lives in ``app/views`` and is a thin UI
layer over the ``ssa`` services (see ``app/state.py``).
"""

import os
import sys

# Make the app runnable with `streamlit run app/main.py` from the repo root:
# add app/ (for state/views/charts) and the repo root (for the ssa package).
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

import styling
from state import current_user, get_workspace, sign_out
from views import ask, auth, dashboard, data, projects

# Page-level config must be the first Streamlit call.
st.set_page_config(page_title="Self-Serve Analytics", layout="wide")
styling.inject()

# Screens available once a project is open.
PROJECT_SCREENS = {
    "Data": data.render,
    "Dashboard": dashboard.render,
    "Ask": ask.render,
}


def render_sidebar(workspace) -> str:
    """Draw the left navigation and return the chosen screen."""
    st.sidebar.markdown(
        '<div class="sidebar-brand">Self-Serve Analytics</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    if workspace is None:
        return "Projects"

    st.sidebar.markdown(
        f'<div class="sidebar-project">{workspace.project.name}</div>',
        unsafe_allow_html=True,
    )
    tables = len(workspace.project.tables)
    st.sidebar.caption(f"{tables} table{'' if tables == 1 else 's'} loaded")
    return st.sidebar.radio("Navigate", ["Projects", *PROJECT_SCREENS], index=1)


def render_account_bar() -> None:
    """Who is signed in, and the way out — top right, out of the way."""
    _, name, action = st.columns([7, 2, 1])
    name.markdown(
        f'<div class="account-name">Signed in as <b>{current_user().username}</b></div>',
        unsafe_allow_html=True,
    )
    if action.button("Sign out", key="sign_out"):
        sign_out()
        st.rerun()


def main() -> None:
    # 1. not signed in -> the only screen is sign in / register
    if current_user() is None:
        auth.render()
        return

    # 2. signed in -> pick a project, then work inside it
    workspace = get_workspace()
    screen = render_sidebar(workspace)
    render_account_bar()
    if workspace is None or screen == "Projects":
        projects.render()
        return
    PROJECT_SCREENS[screen]()


if __name__ == "__main__":
    main()
