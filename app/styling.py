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

/* Streamlit draws its icons as ligatures in a Material font. The rule above
   would replace that font and leave the ligature names showing as raw text
   ("keyboard_double_arrow_left"), so put the icon font back. */
[data-testid="stIconMaterial"],
[class*="material-symbols"],
[class*="material-icons"] {{
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
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


.hero-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
}}

/* --- app shell ---------------------------------------------------------- */

/* Streamlit's own toolbar ("Deploy" and the ⋮ menu) is for whoever runs the
   app, not for the people using it — hide it so the page has one header. */
[data-testid="stToolbar"] {{ display: none; }}
#MainMenu {{ visibility: hidden; }}

/* Reclaim the space the toolbar occupied. */
.block-container {{ padding-top: 2.4rem; }}

.sidebar-brand {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.28rem;
    font-weight: 500;
    line-height: 1.2;
    color: #F5F2EC;
}}

.sidebar-project {{
    font-size: 1rem;
    font-weight: 500;
    color: #E4DED2;
}}

.nav-gap {{ height: 1.2rem; }}

/* Navigation: one quiet block per destination, the current one inverted. */
[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    padding: 0.62rem 0.9rem;
    margin-bottom: 2px;
    border: none;
    border-radius: 9px;
    background: transparent;
    color: #A79F90;
    font-size: 1rem;
    font-weight: 400;
    transition: background .18s ease, color .18s ease;
}}

[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(217, 199, 163, 0.08);
    color: #E4DED2;
}}

/* The active destination. Streamlit marks primary buttons differently across
   versions, so match every form of the attribute. */
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[kind="primaryFormSubmit"],
[data-testid="stSidebar"] [data-testid*="rimary"] > button,
[data-testid="stSidebar"] button[data-testid*="rimary"] {{
    background: #D9C7A3;
    color: #221E18;
    font-weight: 500;
}}

/* Account details sit quietly in the top right, level with the sign-out. */
.account-name {{
    text-align: right;
    font-size: 0.87rem;
    color: #8E8779;
    padding-top: 0.55rem;
    white-space: nowrap;
}}

/* --- page furniture ------------------------------------------------------ */

/* The page title is the largest thing on screen, so it reads first. */
.page-title {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-size: 2.6rem !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em;
    color: #F5F2EC;
    margin: 0.4rem 0 0.3rem;
}}

.page-lede {{
    font-size: 0.98rem;
    color: #8E8779;
    margin: 0 0 1.8rem;
}}

.section-gap {{ height: 1.6rem; }}

/* An empty page should invite one action rather than explain itself. */
.empty-state {{
    text-align: center;
    padding: 3.5rem 0 1.8rem;
}}

.empty-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.7rem;
    font-weight: 500;
    color: #E4DED2;
}}

.empty-lede {{
    font-size: 0.97rem;
    line-height: 1.65;
    color: #8E8779;
    max-width: 26rem;
    margin: 0.8rem auto 0;
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
/* The copy and the buttons arrive with the same movement. The example is not
   listed here on purpose: hiding a component iframe from outside is unreliable
   — if the animation doesn't run the card would stay invisible for good — so
   it fades itself in on its own schedule instead. */
.hero-title, .hero-tags, .hero-slogan, .stButton {
    opacity: 0;
    animation: rise .85s cubic-bezier(.22, .61, .36, 1) forwards;
}

/* These delays must come *after* the `animation` shorthand above: the shorthand
   resets every animation-* property it covers, so putting the delays first
   silently zeroes them and everything appears at once.

   One line at a time down the left column; each takes .85s, so the last lands
   at 2.0s — which is when the example picks up. */
.hero-title  { animation-delay: .15s; }
.hero-tags   { animation-delay: .70s; }
.hero-slogan { animation-delay: 1.15s; }

/* The demonstration runs to about 5.3s. After a half-second pause the page
   lifts to make room, and the two ways in follow — so the product is shown
   before a decision is asked for. Shrinking the top spacer pulls it upward. */
@keyframes lift {
    to { height: clamp(1rem, 4vh, 2.5rem); }
}
.hero-lead {
    animation: lift .9s cubic-bezier(.22, .61, .36, 1) 5.8s forwards;
}
.stButton { animation-delay: 6.0s; }

/* Larger, calmer buttons — they are the page's only call to action. */
.stButton > button {
    padding: 0.85rem 1.4rem;
    font-size: 1.02rem;
    font-weight: 500;
    border-radius: 10px;
}

@media (prefers-reduced-motion: reduce) {
    .hero-tags, .hero-title, .hero-slogan, .stButton, .hero-lead {
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
