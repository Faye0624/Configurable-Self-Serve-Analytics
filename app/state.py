"""Session state for the Streamlit app.

Streamlit re-runs the whole script on every interaction, so the long-lived
objects are stashed in ``st.session_state`` and reused across reruns:

  * the **catalogue** database (accounts + the list of projects) — one per app;
  * the signed-in **user**;
  * the **workspace** for the currently open project — its own database file
    plus one instance of each service.

Switching project throws the workspace away and builds a new one, so a project's
data and configuration never leak into another.

This module holds *no analysis logic*: it only wires the ``ssa`` services
together. All behaviour lives in ``ssa`` (the views stay a thin UI layer).
"""

from dataclasses import dataclass

import streamlit as st

from ssa.db import Database
from ssa.llm import build_default_client
from ssa.models import Project, User
from ssa.services import (
    AuthService,
    CleaningService,
    DataRegistry,
    NLQueryEngine,
    ProfilingService,
    ProjectStore,
    SemanticConfigService,
    TemplateEngine,
    UnlockEngine,
    UsageLimiter,
)

CATALOGUE_DB = "workspace.duckdb"   # accounts + project list
PROJECT_DIR = "projects"            # one <project id>.duckdb per project


@dataclass
class Workspace:
    """The currently open project: its database and the services acting on it."""

    db: Database
    registry: DataRegistry
    project: Project
    profiler: ProfilingService
    cleaner: CleaningService
    config: SemanticConfigService
    unlock: UnlockEngine
    templates: TemplateEngine
    nl: NLQueryEngine


# --- app-wide singletons ---------------------------------------------------- #
def get_catalogue() -> Database:
    if "catalogue_db" not in st.session_state:
        st.session_state.catalogue_db = Database(CATALOGUE_DB)
    return st.session_state.catalogue_db


def get_auth() -> AuthService:
    if "auth" not in st.session_state:
        st.session_state.auth = AuthService(get_catalogue())
    return st.session_state.auth


def get_store() -> ProjectStore:
    if "store" not in st.session_state:
        st.session_state.store = ProjectStore(get_catalogue(), PROJECT_DIR)
    return st.session_state.store


def get_limiter() -> UsageLimiter:
    """Caps model calls per day — a deployed app shares one API key."""
    if "limiter" not in st.session_state:
        try:
            limit = int(st.secrets.get("SSA_DAILY_LLM_LIMIT", 100))
        except Exception:
            limit = 100
        st.session_state.limiter = UsageLimiter(get_catalogue(), daily_limit=limit)
    return st.session_state.limiter


# --- signed-in user --------------------------------------------------------- #
def current_user() -> User | None:
    return st.session_state.get("user")


def sign_in(user: User) -> None:
    st.session_state.user = user
    close_workspace()


def sign_out() -> None:
    st.session_state.pop("user", None)
    close_workspace()


# --- the open project ------------------------------------------------------- #
def open_project(project: Project) -> None:
    """Make `project` the active one, rebuilding its workspace from its own file."""
    close_workspace()
    st.session_state.project_id = project.id


def close_workspace() -> None:
    st.session_state.pop("workspace", None)
    st.session_state.pop("project_id", None)


def get_workspace() -> Workspace | None:
    """Workspace for the open project, or None if no project is open."""
    if "workspace" in st.session_state:
        return st.session_state.workspace

    project_id = st.session_state.get("project_id")
    user = current_user()
    if not project_id or user is None:
        return None

    store = get_store()
    project = next((p for p in store.list_projects(user.username)
                    if p.id == project_id), None)
    if project is None:          # deleted in another tab
        close_workspace()
        return None

    # The project's own database holds its tables and its query history.
    db = store.open_data_db(project)
    registry = DataRegistry(db)
    registry.tables = {t.name: t for t in project.tables}
    st.session_state.workspace = Workspace(
        db=db,
        registry=registry,
        project=project,
        profiler=ProfilingService(),
        cleaner=CleaningService(),
        config=SemanticConfigService(),
        unlock=UnlockEngine(),
        templates=TemplateEngine(db),
        nl=NLQueryEngine(db, build_default_client(), history_db=db,
                         limiter=get_limiter()),
    )
    return st.session_state.workspace


def save_current_project() -> None:
    """Persist the open project's configuration."""
    ws = st.session_state.get("workspace")
    if ws is not None:
        get_store().save(ws.project)
