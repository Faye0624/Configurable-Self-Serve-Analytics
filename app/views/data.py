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

from ssa.models import Role
from ssa.services import safe_table_name
from state import Workspace, get_workspace

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


# --------------------------------------------------------------------------- #
# Upload wizard
# --------------------------------------------------------------------------- #
def _wizard(ws: Workspace) -> None:
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
        st.session_state.wiz_step = 2
        st.rerun()


def _step_clean(ws: Workspace) -> None:
    df = st.session_state.get("wiz_df")
    if df is None:
        st.info("Upload a file in step 1 first.")
        return

    cleaned, actions = ws.cleaner.clean(df)
    issues = ws.cleaner.flag_suspicious(df)
    st.session_state.wiz_cleaned = cleaned

    st.markdown("**Auto-clean applied**")
    if actions:
        for action in actions:
            st.write(f"• {action}")
    else:
        st.caption("No automatic fixes were necessary.")

    st.markdown("**Flagged for your review**")
    if issues:
        for issue in issues:
            st.warning(issue)
        st.caption("The LLM API isn't wired in yet — AI-assisted fix suggestions "
                   "may appear here later (part of US5). For now these issues are "
                   "surfaced for you to review.")
    else:
        st.caption("No suspicious columns detected.")

    back, forward = st.columns(2)
    if back.button("← Back"):
        st.session_state.wiz_step = 1
        st.rerun()
    if forward.button("Next: Configure →", type="primary"):
        st.session_state.wiz_step = 3
        st.rerun()


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
    _role_editor(ws, table)

    back, done = st.columns(2)
    if back.button("← Back", key="cfg_back"):
        st.session_state.wiz_step = 2
        st.rerun()
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
            _role_editor(ws, table)
            if st.button("Preview rows", key=f"preview_{table.name}"):
                st.dataframe(
                    ws.db.query(f'SELECT * FROM "{table.name}" LIMIT 50'),
                    width="stretch",
                )


# --------------------------------------------------------------------------- #
# Shared: roles & keys editor (US6/US7/US8)
# --------------------------------------------------------------------------- #
def _role_editor(ws: Workspace, table) -> None:
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
            key=f"role_{table.name}_{col.name}", label_visibility="collapsed",
            format_func=lambda r: str(r).title(),
        )
        is_key = row[2].checkbox(
            "Join key", value=col.is_join_key,
            key=f"key_{table.name}_{col.name}", label_visibility="collapsed",
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
