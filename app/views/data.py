"""Data screen — upload wizard and the uploaded-tables list.

Two tabs:
  * **Upload data** — a 3-step wizard: Upload → Clean → Configure. Each step
    calls one service (registry / cleaning / profiling + semantic config).
  * **Uploaded tables** — every table in the project, each with its roles &
    keys editor so the configuration can be revisited (drives progressive
    unlock live).

The view only orchestrates and renders; profiling, cleaning, and configuration
all happen inside ``ssa``.
"""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ssa.models import Role
from ssa.services import safe_table_name
from state import Workspace, get_workspace, save_current_project

# Order shown in the role dropdown.
ROLE_OPTIONS = [
    Role.UNASSIGNED,
    Role.IDENTIFIER,
    Role.DATE,
    Role.MEASURE,
    Role.DIMENSION,
]

# Wizard keys kept in session_state, cleared when a table is finished.
_WIZ_KEYS = ["wiz_step", "wiz_df", "wiz_name", "wiz_source", "wiz_cleaned", "wiz_stored"]


def _go_to_step(step: int) -> None:
    """Move the wizard to a step and scroll back to the top of the page.

    Streamlit keeps the scroll position across reruns, which would otherwise
    drop the user halfway down the next step.
    """
    st.session_state.wiz_step = step
    st.session_state.scroll_to_top = True
    st.rerun()


def _scroll_to_top_if_requested() -> None:
    """Scroll the page back to the top after a step change.

    Streamlit has no API for this and renames its layout containers between
    versions, so we try the known selectors and then fall back to whatever
    element is actually scrolled. It runs a few times because the new step is
    still rendering when the script first fires.
    """
    if not st.session_state.pop("scroll_to_top", False):
        return
    components.html(
        """
        <script>
        const toTop = () => {
            const doc = window.parent.document;
            const known = ['[data-testid="stMain"]', 'section.stMain',
                           'section.main', '.stMainBlockContainer',
                           '[data-testid="stAppViewContainer"]'];
            known.forEach(sel => {
                const el = doc.querySelector(sel);
                if (el) el.scrollTop = 0;
            });
            // fallback: anything that is currently scrolled down
            doc.querySelectorAll('div, section').forEach(el => {
                if (el.scrollTop > 0) el.scrollTop = 0;
            });
            if (doc.scrollingElement) doc.scrollingElement.scrollTop = 0;
            window.parent.scrollTo(0, 0);
        };
        toTop();
        [30, 120, 300, 600].forEach(ms => setTimeout(toTop, ms));
        </script>
        """,
        height=0,
    )


def render() -> None:
    ws = get_workspace()
    st.title("Data")
    upload_tab, tables_tab = st.tabs(
        ["Upload data", f"Uploaded tables ({len(ws.project.tables)})"]
    )
    with upload_tab:
        _wizard(ws)
    with tables_tab:
        _uploaded_tables(ws)

    # Persist the project config after any change so it survives a restart.
    save_current_project()


# --------------------------------------------------------------------------- #
# Upload wizard
# --------------------------------------------------------------------------- #
def _wizard(ws: Workspace) -> None:
    _scroll_to_top_if_requested()
    step = st.session_state.get("wiz_step", 1)
    labels = ["1. Upload", "2. Clean", "3. Configure"]
    st.caption("  →  ".join(f"**{l}**" if i + 1 == step else l
                            for i, l in enumerate(labels)))
    st.divider()
    (_step_upload, _step_clean, _step_configure)[step - 1](ws)


def _step_upload(ws: Workspace) -> None:
    upload = st.file_uploader("Drop a CSV file to upload", type=["csv"])
    if upload is None:
        st.caption("Tables accumulate — you can upload several, one at a time (US1).")
        return

    df = pd.read_csv(upload)
    st.session_state.wiz_df = df
    st.session_state.wiz_name = safe_table_name(upload.name)
    st.session_state.wiz_source = upload.name
    st.success(
        f"Loaded **{upload.name}** → table `{st.session_state.wiz_name}` — "
        f"{len(df):,} rows × {len(df.columns)} columns"
    )
    st.dataframe(df.head(20), width="stretch")
    if st.button("Next: Clean →", type="primary"):
        _go_to_step(2)


def _step_clean(ws: Workspace) -> None:
    """Cleaning is opt-in: show what could be fixed, apply only what's ticked."""
    df = st.session_state.get("wiz_df")
    if df is None:
        st.info("Upload a file in step 1 first.")
        return

    options = ws.cleaner.detect(df)          # detect only — nothing is changed
    issues = ws.cleaner.flag_suspicious(df)

    # --- what we found, with the offending rows shown --------------------- #
    st.markdown("### Data quality check")
    if options:
        st.caption("We found the following in your file.")
        for opt in options:
            with st.container(border=True):
                st.markdown(f"**{opt.label}**")
                st.caption(opt.detail)
                if opt.rows is not None and not opt.rows.empty:
                    st.dataframe(opt.rows, width="stretch", hide_index=True)
    else:
        st.success("Your data looks clean — no extra spaces or duplicate rows found.")

    if issues:
        with st.container(border=True):
            st.markdown("**Potential data quality issues**")
            st.caption("Flagged for your review — these require domain knowledge, "
                       "so they are not fixed automatically.")
            for issue in issues:
                st.warning(issue)

    # --- ask whether to clean --------------------------------------------- #
    approved: set[str] = set()
    if options:
        st.markdown("### Clean the data before you configure it?")
        choice = st.radio(
            "Clean the data before you configure it?",
            ["No, use my data as it is", "Yes, clean it"],
            index=0, key="clean_choice", label_visibility="collapsed",
        )
        if choice.startswith("Yes"):
            picked = st.multiselect(
                "What to fix",
                [o.key for o in options],
                default=[o.key for o in options],
                format_func=lambda k: next(o.label for o in options if o.key == k),
            )
            approved = set(picked)

    cleaned, actions = ws.cleaner.apply(df, approved)
    st.session_state.wiz_cleaned = cleaned

    st.divider()
    back, forward = st.columns(2)
    if back.button("← Back"):
        _go_to_step(1)
    if forward.button("Next: Configure →", type="primary"):
        _go_to_step(3)


def _step_configure(ws: Workspace) -> None:
    cleaned = st.session_state.get("wiz_cleaned")
    name = st.session_state.get("wiz_name")
    if cleaned is None or name is None:
        st.info("Complete steps 1–2 first.")
        return

    # Store + profile + suggest exactly once for this upload.
    if st.session_state.get("wiz_stored") != name:
        table = ws.registry.add_dataframe(
            name, cleaned, source_file=st.session_state.get("wiz_source", "")
        )
        ws.profiler.profile(cleaned, table.columns)   # US2
        ws.config.suggest(table)                       # US8: prefill roles/keys
        # Replace any earlier table of the same name (incremental re-upload).
        ws.project.tables = [t for t in ws.project.tables if t.name != name] + [table]
        st.session_state.wiz_stored = name

    table = next(t for t in ws.project.tables if t.name == name)
    st.success(f"Stored as `{table.name}`. Confirm the roles and join keys below.")
    _role_editor(ws, table, scope="wizard")

    back, done = st.columns(2)
    if back.button("← Back", key="cfg_back"):
        _go_to_step(2)
    if done.button("Save & finish", type="primary"):
        for key in _WIZ_KEYS:
            st.session_state.pop(key, None)
        st.toast(f"Saved {table.name}. Open the Dashboard to see what unlocked.")
        st.rerun()


# --------------------------------------------------------------------------- #
# Uploaded tables
# --------------------------------------------------------------------------- #
def _uploaded_tables(ws: Workspace) -> None:
    if not ws.project.tables:
        st.info("No tables yet — add one in the **Upload data** tab.")
        return

    for table in ws.project.tables:
        header = f"{table.name} · {table.row_count:,} rows × {len(table.columns)} cols"
        with st.expander(header):
            _role_editor(ws, table, scope="tables")
            if st.button("Preview rows", key=f"preview_{table.name}"):
                st.dataframe(
                    ws.db.query(f'SELECT * FROM "{table.name}" LIMIT 50'),
                    width="stretch",
                )


# --------------------------------------------------------------------------- #
# Shared: roles & keys editor (US6/US7/US8)
# --------------------------------------------------------------------------- #
def _role_editor(ws: Workspace, table, scope: str) -> None:
    # `scope` disambiguates widget keys: the same table's editor is rendered
    # both in the upload wizard and in the "Uploaded tables" tab, and Streamlit
    # renders every tab, so the keys must differ between the two call sites.
    st.markdown("**Configure — roles & keys**")
    head = st.columns([3, 3, 2, 4])
    head[0].caption("Column")
    head[1].caption("Role")
    head[2].caption("Join key")
    head[3].caption("Profile")

    for col in table.columns:
        row = st.columns([3, 3, 2, 4])
        row[0].write(f"`{col.name}`")

        role = row[1].selectbox(
            "Role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(col.role),
            key=f"role_{scope}_{table.name}_{col.name}", label_visibility="collapsed",
            format_func=lambda r: str(r).title(),
        )
        is_key = row[2].checkbox(
            "Join key", value=col.is_join_key,
            key=f"key_{scope}_{table.name}_{col.name}", label_visibility="collapsed",
        )
        row[3].caption(
            f"{col.data_type} · {col.null_pct}% null · {col.distinct_count} distinct"
        )

        # Push the widget values back through the service (US6/US7).
        ws.config.set_role(table, col.name, role)
        if is_key:
            ws.config.set_join_key(table, col.name, col.key_name or col.name)
        else:
            ws.config.clear_join_key(table, col.name)
