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

/* Display type. Streamlit's own heading styles are more specific, so these
   need !important to win. */
h1, h2, .hero-title {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em;
}}

.hero-title {{
    font-size: clamp(3rem, 6.4vw, 4.6rem) !important;
    line-height: 1.02;
    color: #F5F2EC;
    margin: 1.1rem 0 0;
}}

/* The slogan answers the title in the same voice, one size down. */
.hero-slogan {{
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-weight: 300;
    font-size: clamp(1.5rem, 2.4vw, 1.95rem);
    line-height: 1.25;
    color: #CFC7B8;
    margin: 1.5rem 0 0;
}}

/* One plain sentence for anyone who wants to know what it actually does. */
.hero-support {{
    font-family: 'Manrope', sans-serif;
    font-size: 0.98rem;
    line-height: 1.65;
    color: #8E8779;
    max-width: 30rem;
    margin: 1.1rem 0 0;
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

/* Give the hero room to breathe: drop it down the page and space it out, so
   it reads as a landing page rather than a form at the top of a screen. */
.hero-lead {{ height: clamp(3rem, 12vh, 8rem); }}
.hero-spacer {{ height: 2.6rem; }}

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
/* The title lands first, then the tags above it, then the lines beneath. */
.hero-title   { animation-delay: .15s; }
.hero-tags    { animation-delay: .70s; }
.hero-slogan  { animation-delay: 1.15s; }
.hero-support { animation-delay: 1.55s; }

.hero-title, .hero-tags, .hero-slogan, .hero-support, .stButton, iframe {
    opacity: 0;
    animation: rise .85s cubic-bezier(.22, .61, .36, 1) forwards;
}

/* The example arrives once the copy has settled... */
iframe { animation-delay: 1.7s; }

/* ...and the two ways in wait until it has played through once, so the
   demonstration gets watched before the page asks for a decision. */
.stButton { animation-delay: 4.7s; }

@media (prefers-reduced-motion: reduce) {
    .hero-tags, .hero-title, .hero-slogan, .hero-support, .stButton, iframe {
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
