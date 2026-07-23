"""Session state for the Streamlit app.

Streamlit re-runs the whole script on every interaction, so the long-lived
objects — the DuckDB connection, the registered project, and one instance of
each service — are stashed in ``st.session_state`` and reused across reruns.

This module holds *no analysis logic*: it only wires the ``ssa`` services
together. All behaviour lives in ``ssa`` (the views stay a thin UI layer).
"""

from dataclasses import dataclass

import streamlit as st

from ssa.db import Database
from ssa.models import Project
from ssa.services import (
    CleaningService,
    DataRegistry,
    ProfilingService,
    SemanticConfigService,
    TemplateEngine,
    UnlockEngine,
)


@dataclass
class Workspace:
    """One user session: the database, the project, and the services."""

    db: Database
    registry: DataRegistry
    project: Project
    profiler: ProfilingService
    cleaner: CleaningService
    config: SemanticConfigService
    unlock: UnlockEngine
    templates: TemplateEngine


def get_workspace() -> Workspace:
    """Return this session's Workspace, creating it on first use."""
    if "workspace" not in st.session_state:
        db = Database()  # in-memory DuckDB, scoped to this session
        st.session_state.workspace = Workspace(
            db=db,
            registry=DataRegistry(db),
            project=Project(name="Demo project"),
            profiler=ProfilingService(),
            cleaner=CleaningService(),
            config=SemanticConfigService(),
            unlock=UnlockEngine(),
            templates=TemplateEngine(db),
        )
    return st.session_state.workspace
