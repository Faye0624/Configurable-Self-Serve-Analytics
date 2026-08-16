"""Web fonts and the few style rules Streamlit's theme can't express.

The theme in `.streamlit/config.toml` sets the colours; this adds the
typography — Fraunces for display text and Manrope for everything else — plus
the small landing-page classes those headings need.
"""

import streamlit as st

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Fraunces:opsz,wght@9..144,300..600"
    "&family=Manrope:wght@400;500;600&display=swap"
)

_CSS = f"""
<style>
@import url('{_FONTS}');

html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
}}

/* Display type: only for the landing hero and page titles. */
h1, h2, .hero-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-weight: 500;
    letter-spacing: -0.02em;
}}

.hero-title {{
    font-size: clamp(2.4rem, 5.2vw, 3.6rem);
    line-height: 1.04;
    color: #F5F2EC;
    margin: 0.6rem 0 0;
}}

.hero-slogan {{
    font-size: 1.05rem;
    color: #A79F90;
    margin: 0.9rem 0 0;
}}

.hero-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
}}

.hero-tag {{
    font-size: 0.66rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: #C6B694;
    border: 1px solid #3D3830;
    border-radius: 999px;
    padding: 4px 11px;
    white-space: nowrap;
}}

/* Give the hero room to breathe. */
.hero-spacer {{ height: 1.6rem; }}
</style>
"""


def inject() -> None:
    """Load the fonts and base styles. Safe to call on every rerun."""
    st.markdown(_CSS, unsafe_allow_html=True)
