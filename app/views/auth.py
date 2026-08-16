"""Landing page and account access.

Everything before signing in lives here. The landing view introduces the
product and offers two ways in; choosing one swaps the left column for that
form, so the page never navigates away from the introduction.
"""

import streamlit as st

import demo_card
import styling
from ssa.services import AuthError
from state import get_auth, sign_in

LANDING, SIGN_IN, REGISTER = "landing", "sign_in", "register"


def render() -> None:
    view = st.session_state.get("auth_view", LANDING)
    left, right = st.columns([1.05, 1], gap="large")

    with left:
        if view == SIGN_IN:
            _sign_in_form()
        elif view == REGISTER:
            _register_form()
        else:
            _intro()

    with right:
        # Drop the example down to sit level with the headline.
        st.markdown('<div class="hero-lead"></div>', unsafe_allow_html=True)
        _demo_card()

    # The two ways in sit centred beneath both columns, so the choice reads as
    # the page's single next step rather than part of the copy.
    if view == LANDING:
        _ways_in()


def _go(view: str) -> None:
    st.session_state.auth_view = view
    st.rerun()


# --- left column ------------------------------------------------------------ #
TAGS = ("configurable", "transparent", "self-hostable")


def _intro() -> None:
    styling.landing_motion()
    tags = "".join(f'<span class="hero-tag">{t}</span>' for t in TAGS)
    st.markdown(
        f'<div class="hero-lead"></div>'
        f'<div class="hero-tags">{tags}</div>'
        f'<h1 class="hero-title">Self-Serve<br>Analytics</h1>'
        f'<p class="hero-slogan">Ask your data anything.</p>',
        unsafe_allow_html=True,
    )


def _ways_in() -> None:
    """The two entry points, centred below the page."""
    st.markdown('<div class="hero-spacer"></div>', unsafe_allow_html=True)
    _, sign_in_col, register_col, _ = st.columns([1.35, 1, 1, 1.35])
    if sign_in_col.button("Sign in", type="primary", width="stretch"):
        _go(SIGN_IN)
    if register_col.button("Create an account", width="stretch"):
        _go(REGISTER)


def _sign_in_form() -> None:
    styling.form_motion()
    st.subheader("Sign in")
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
    _back()


def _register_form() -> None:
    styling.form_motion()
    st.subheader("Create an account")
    with st.form("register"):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", type="primary")
    if submitted:
        if password != confirm:
            st.error("The two passwords don't match.")
        else:
            try:
                sign_in(get_auth().register(username, password))
                st.rerun()
            except AuthError as exc:
                st.error(str(exc))
    _back()


def _back() -> None:
    if st.button("← Back"):
        _go(LANDING)


# --- right column ----------------------------------------------------------- #
def _demo_card() -> None:
    """A worked example of the product: a question, its SQL, and the answer."""
    demo_card.render()
