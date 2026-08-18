"""UI tests for the two routing decisions the app makes after sign-in.

Everything else is tested at the service level; these run the real Streamlit
script headlessly (``AppTest``) because the behaviour under test *is* the
routing — which screen appears, and what the sidebar highlights.

Two notes on driving AppTest:
  * the element tree it exposes is the one from the first pass of the script,
    so a widget interacted with before a ``st.rerun()`` cannot be reused
    afterwards — each block below starts from a fresh ``AppTest``;
  * ``at.session_state`` is not a plain dict, so use ``in`` and ``[]``
    rather than ``.get()``.
"""

import sys
from pathlib import Path

import pytest

from ssa.db import Database
from ssa.services import AuthService, ProjectStore

APP = Path(__file__).resolve().parents[1] / "app" / "main.py"
pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


@pytest.fixture
def signed_in(tmp_path, monkeypatch):
    """A signed-in user with no projects, in a throwaway working directory.

    The app resolves its catalogue and project files relative to the working
    directory, so moving there keeps the test off the developer's real data.
    """
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(APP.parent))
    user = AuthService(Database("workspace.duckdb")).register("faye", "pw12345678")
    yield user
    sys.path.remove(str(APP.parent))


def _app(user, **state):
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.session_state["user"] = user
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def test_first_project_is_created_from_the_empty_state(signed_in):
    """With no projects, the page is one invitation — and it works."""
    at = _app(signed_in)
    assert any("No projects yet" in m.value for m in at.markdown)

    at.text_input(key="first_project_name").set_value("Olist demo")
    at.button(key="FormSubmitter:first_project-Create a project").click().run()

    assert not at.exception
    assert "project_id" in at.session_state
    # Opening a project should land on its data, not leave the user on a menu.
    assert at.session_state["screen"] == "Data"

    saved = ProjectStore(Database("workspace.duckdb"), "projects").list_projects("faye")
    assert [p.name for p in saved] == ["Olist demo"]


def test_sidebar_marks_the_current_screen_and_switches(signed_in):
    """The active destination is the primary (inverted) button; clicking moves."""
    store = ProjectStore(Database("workspace.duckdb"), "projects")
    project = store.create("faye", "Olist demo")

    at = _app(signed_in, project_id=project.id, screen="Data")
    assert [b.label for b in at.sidebar.button] == \
        ["Projects", "Data", "Dashboard", "Ask"]
    assert [b.proto.type for b in at.sidebar.button] == \
        ["secondary", "primary", "secondary", "secondary"]

    at.sidebar.button(key="nav_Ask").click().run()
    assert not at.exception
    assert at.session_state["screen"] == "Ask"
    assert [b.proto.type for b in at.sidebar.button] == \
        ["secondary", "secondary", "secondary", "primary"]


def test_projects_screen_is_reachable_while_a_project_is_open(signed_in):
    """Going back to Projects lists them without closing the open one."""
    store = ProjectStore(Database("workspace.duckdb"), "projects")
    project = store.create("faye", "Olist demo")

    at = _app(signed_in, project_id=project.id, screen="Data")
    at.sidebar.button(key="nav_Projects").click().run()

    assert not at.exception
    assert at.session_state["screen"] == "Projects"
    assert any("Olist demo" in m.value for m in at.markdown)
    assert at.session_state["project_id"] == project.id
