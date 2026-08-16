"""Projects screen — create, open, rename and delete projects (US20).

Each project is isolated: its own tables, its own semantic configuration and its
own query history. Deleting a project destroys data, so it asks for explicit
confirmation first (supervisor feedback).
"""

import streamlit as st

from state import current_user, get_store, open_project


def render() -> None:
    user = current_user()
    store = get_store()
    projects = store.list_projects(user.username)

    st.markdown('<h1 class="page-title">Projects</h1>', unsafe_allow_html=True)

    if not projects:
        _empty_state(store, user.username)
        return

    st.markdown(
        '<p class="page-lede">Each project keeps its own data, configuration '
        'and query history.</p>',
        unsafe_allow_html=True,
    )
    for project in projects:
        _project_card(store, project)

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    with st.expander("New project"):
        _create_form(store, user.username, key="new_project")


def _empty_state(store, owner: str) -> None:
    """Nothing to show yet, so the page becomes one clear invitation."""
    _, middle, _ = st.columns([1, 2.2, 1])
    with middle:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-title">No projects yet</div>'
            '<div class="empty-lede">A project holds your data, how you\'ve '
            'described it, and everything you ask about it.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        _create_form(store, owner, key="first_project",
                     button_label="Create a project")


def _create_form(store, owner: str, key: str,
                 button_label: str = "Create project") -> None:
    with st.form(key, clear_on_submit=True):
        name = st.text_input("Project name", placeholder="e.g. Olist e-commerce",
                             label_visibility="collapsed")
        created = st.form_submit_button(button_label, type="primary",
                                        width="stretch")
    if created:
        if not name.strip():
            st.error("Please give the project a name.")
            return
        open_project(store.create(owner, name))
        st.rerun()


def _project_card(store, project) -> None:
    with st.container(border=True):
        left, right = st.columns([4, 1])
        left.markdown(f"**{project.name}**")
        tables = len(project.tables)
        left.caption(f"{tables} table{'' if tables == 1 else 's'}")

        if right.button("Open", key=f"open_{project.id}", type="primary"):
            open_project(project)
            st.rerun()

        with st.expander("Settings"):
            _rename(store, project)
            _delete(store, project)


def _rename(store, project) -> None:
    new_name = st.text_input("Rename", value=project.name, key=f"name_{project.id}")
    if new_name.strip() and new_name != project.name:
        if st.button("Save name", key=f"save_{project.id}"):
            project.name = new_name.strip()
            store.save(project)
            st.rerun()


def _delete(store, project) -> None:
    """Deleting removes the project's data, so confirm before doing it."""
    confirm_key = f"confirm_delete_{project.id}"

    if not st.session_state.get(confirm_key):
        if st.button("Delete project", key=f"del_{project.id}"):
            st.session_state[confirm_key] = True
            st.rerun()
        return

    st.warning(f"Delete **{project.name}**? Its uploaded data, configuration and "
               "query history will be permanently removed.")
    yes, no = st.columns(2)
    if yes.button("Yes, delete it", key=f"yes_{project.id}", type="primary"):
        store.delete(project)
        st.session_state.pop(confirm_key, None)
        if st.session_state.get("project_id") == project.id:
            st.session_state.pop("workspace", None)
            st.session_state.pop("project_id", None)
        st.rerun()
    if no.button("No, keep it", key=f"no_{project.id}"):
        st.session_state.pop(confirm_key, None)
        st.rerun()
