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

@keyframes rise {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
</style>
"""

# Motion for the landing page only. It delays the buttons and the example, so
# it must never reach the rest of the app — a 1.45s delay on every button would
# make the whole product feel broken.
_LANDING_MOTION = """
<style>
.hero-tags, .hero-title, .hero-slogan {
    opacity: 0;
    animation: rise .85s cubic-bezier(.22, .61, .36, 1) forwards;
}
.hero-tags   { animation-delay: .10s; }
.hero-title  { animation-delay: .55s; }
.hero-slogan { animation-delay: 1.00s; }

/* The buttons and the worked example arrive together, once the copy has settled. */
.stButton, iframe {
    opacity: 0;
    animation: rise .85s cubic-bezier(.22, .61, .36, 1) forwards;
    animation-delay: 1.45s;
}

@media (prefers-reduced-motion: reduce) {
    .hero-tags, .hero-title, .hero-slogan, .stButton, iframe {
        animation: none; opacity: 1;
    }
}
</style>
"""

# A quick fade when a form replaces the introduction — no delay, so nothing
# ever feels unresponsive.
_FORM_MOTION = """
<style>
.stForm { animation: rise .45s cubic-bezier(.22, .61, .36, 1); }
@media (prefers-reduced-motion: reduce) { .stForm { animation: none; } }
</style>
"""


def inject() -> None:
    """Load the fonts and base styles. Safe to call on every rerun."""
    st.markdown(_CSS, unsafe_allow_html=True)


def landing_motion() -> None:
    """Stagger the landing page in. Call only from the landing view."""
    st.markdown(_LANDING_MOTION, unsafe_allow_html=True)


def form_motion() -> None:
    """Fade a sign-in or registration form in as it replaces the introduction."""
    st.markdown(_FORM_MOTION, unsafe_allow_html=True)
