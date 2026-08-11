"""Sign-in / registration screen.

Shown until someone is signed in; every other screen is behind it. Passwords go
straight to ``AuthService`` (hashed there) — this view only collects them.
"""

import streamlit as st

from ssa.services import AuthError
from state import get_auth, sign_in


def render() -> None:
    st.title("Self-Serve Analytics")
    st.caption("Upload your data, configure what each column means, and get "
               "analyses and natural-language answers — no SQL required.")
    st.divider()

    sign_in_tab, register_tab = st.tabs(["Sign in", "Create an account"])
    with sign_in_tab:
        _sign_in_form()
    with register_tab:
        _register_form()


def _sign_in_form() -> None:
    with st.form("sign_in"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        try:
            sign_in(get_auth().login(username, password))
            st.rerun()
        except AuthError as exc:
            st.error(str(exc))


def _register_form() -> None:
    with st.form("register"):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", type="primary")
    if submitted:
        if password != confirm:
            st.error("The two passwords don't match.")
            return
        try:
            sign_in(get_auth().register(username, password))
            st.rerun()
        except AuthError as exc:
            st.error(str(exc))
