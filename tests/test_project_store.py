"""Tests for multiple projects (US20): isolation, persistence and deletion."""

import pytest

from ssa.db import Database
from ssa.models import Role
from ssa.services import DataRegistry, ProjectStore, SemanticConfigService


@pytest.fixture
def store(db, tmp_path):
    return ProjectStore(db, tmp_path / "projects")


def test_projects_are_listed_per_owner(store):
    store.create("alice", "Olist")
    store.create("alice", "Music")
    store.create("bob", "Bob's project")

    assert {p.name for p in store.list_projects("alice")} == {"Olist", "Music"}
    assert [p.name for p in store.list_projects("bob")] == ["Bob's project"]


def test_config_survives_a_restart(store, orders_df):
    project = store.create("alice", "Olist")
    registry = DataRegistry(store.open_data_db(project))
    table = registry.add_dataframe("orders", orders_df)
    SemanticConfigService().set_role(table, "price", Role.MEASURE)
    project.tables.append(table)
    store.save(project)

    reopened = next(p for p in store.list_projects("alice") if p.id == project.id)
    roles = {c.name: c.role for c in reopened.tables[0].columns}
    assert roles["price"] == Role.MEASURE
    assert "orders" in store.open_data_db(reopened).list_tables()


def test_projects_do_not_share_tables(store, orders_df):
    first = store.create("alice", "First")
    second = store.create("alice", "Second")

    DataRegistry(store.open_data_db(first)).add_dataframe("orders", orders_df)

    # the same table name in another project is a different, separate table
    assert "orders" in store.open_data_db(first).list_tables()
    assert "orders" not in store.open_data_db(second).list_tables()


def test_delete_removes_project_and_its_data(store, orders_df):
    project = store.create("alice", "Doomed")
    DataRegistry(store.open_data_db(project)).add_dataframe("orders", orders_df)
    path = store.data_path(project)
    assert path.exists()

    store.delete(project)

    assert store.list_projects("alice") == []
    assert not path.exists()


def test_a_new_project_starts_empty(store):
    project = store.create("alice", "Fresh")
    assert project.tables == []
    assert project.owner == "alice"
    assert Database(str(store.data_path(project))).list_tables() == []
