"""Streamlit entry point for the Self-Serve Analytics app.

Run locally with:
    streamlit run app/main.py

Right now this is only the shell: the app title and a (disabled) navigation
placeholder that shows the planned flow. Each screen — Projects, Data,
Dashboard, Ask — is wired up in later steps as the underlying services exist.
"""

import streamlit as st

# Page-level config must be the first Streamlit call.
st.set_page_config(page_title="Self-Serve Analytics", layout="wide")


def render_sidebar() -> None:
    """Draw the left navigation.

    The options are disabled for now because the screens don't exist yet;
    they are enabled one by one as we build the corresponding services.
    """
    st.sidebar.title("Self-Serve Analytics")
    st.sidebar.caption("configurable · transparent · self-hostable")
    st.sidebar.radio(
        "Navigate",
        ["Projects", "Data", "Dashboard", "Ask"],
        index=0,
        disabled=True,  # unlocked step by step in later commits
    )


def render_home() -> None:
    """Draw the main landing area."""
    st.title("Self-Serve Analytics")
    st.write(
        "Upload your data, let the tool clean and configure it, and get "
        "analyses and natural-language answers — no SQL required."
    )
    st.info("Project scaffold — screens are added step by step.")


def main() -> None:
    render_sidebar()
    render_home()


if __name__ == "__main__":
    main()
