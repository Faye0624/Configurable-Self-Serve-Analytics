"""Tests for progressive unlocking (US9-US11, covers TC-9/TC-10).

The engine decides which analyses a project can run. An analysis unlocks when a
single *connected* group of tables — tables joined by a shared key — together
provides every role that analysis needs. When it doesn't unlock, the engine says
why, which is what the dashboard shows the user.
"""

import pytest

from ssa.models import Column, DatasetTable, Project, Role
from ssa.services import UnlockEngine


@pytest.fixture
def engine():
    return UnlockEngine()


def _result(results, template_name):
    return next(r for r in results if r.template.name == template_name)


def _table(name, roles: dict, join_key: tuple | None = None) -> DatasetTable:
    """A table whose columns carry the given roles, optionally with a join key."""
    columns = [Column(col, "object", role=role) for col, role in roles.items()]
    if join_key:
        col_name, key_name = join_key
        columns.append(Column(col_name, "object", is_join_key=True, key_name=key_name))
    return DatasetTable(name, columns)


# --- everything configured -> everything unlocks (TC-9) ---------------------- #
def test_fully_configured_project_unlocks_all_analyses(engine, configured_project):
    results = engine.evaluate(configured_project)
    assert all(r.unlocked for r in results)
    assert {r.template.name for r in results} == {
        "Key metrics", "Cohort / retention", "RFM"}


# --- missing roles -> locked, with the reason (TC-10a) ----------------------- #
def test_a_measure_alone_unlocks_only_key_metrics(engine):
    project = Project("p", [_table("sales", {"amount": Role.MEASURE})])
    results = engine.evaluate(project)

    assert _result(results, "Key metrics").unlocked is True
    assert _result(results, "Cohort / retention").unlocked is False
    assert _result(results, "RFM").unlocked is False


def test_lock_reason_names_the_missing_roles(engine):
    project = Project("p", [_table("sales", {"amount": Role.MEASURE})])
    reason = _result(engine.evaluate(project), "Cohort / retention").reason

    assert "date" in reason and "identifier" in reason


def test_lock_reason_is_short_and_says_it_without_jargon(engine):
    """The reason has to work for someone who does not know the vocabulary."""
    project = Project("p", [_table("visits", {"customer": Role.IDENTIFIER,
                                              "when": Role.DATE})])
    reason = _result(engine.evaluate(project), "Key metrics").reason

    assert reason == "Needs an amount column (measure)."   # plain, and one line


def test_an_empty_project_locks_everything(engine):
    results = engine.evaluate(Project("empty"))
    assert not any(r.unlocked for r in results)
    assert all(r.reason for r in results)          # every lock is explained


def test_adding_the_missing_role_unlocks_the_analysis(engine):
    """The 'progressive' part: configure more, and more becomes available."""
    table = _table("events", {"customer": Role.IDENTIFIER})
    project = Project("p", [table])
    assert _result(engine.evaluate(project), "Cohort / retention").unlocked is False

    table.columns.append(Column("when", "object", role=Role.DATE))
    assert _result(engine.evaluate(project), "Cohort / retention").unlocked is True


# --- roles spread across joinable tables (US11) ------------------------------ #
def test_roles_in_two_tables_sharing_a_key_unlock_together(engine):
    """identifier+date in one table, measure in another, joined on 'customer'."""
    project = Project("p", [
        _table("visits", {"customer_id": Role.IDENTIFIER, "visited_at": Role.DATE},
               join_key=("cust_key", "customer")),
        _table("spend", {"amount": Role.MEASURE},
               join_key=("cust_key", "customer")),
    ])
    assert _result(engine.evaluate(project), "RFM").unlocked is True


# --- roles present but not joinable -> locked, with a different reason (TC-10b) #
def test_unjoinable_tables_stay_locked(engine):
    project = Project("p", [
        _table("visits", {"customer_id": Role.IDENTIFIER, "visited_at": Role.DATE}),
        _table("spend", {"amount": Role.MEASURE}),      # no shared key
    ])
    result = _result(engine.evaluate(project), "RFM")

    assert result.unlocked is False
    # A different problem, so a different instruction: connect the files.
    assert "separate files" in result.reason and "key" in result.reason


def test_different_keys_do_not_connect_tables(engine):
    project = Project("p", [
        _table("visits", {"customer_id": Role.IDENTIFIER, "visited_at": Role.DATE},
               join_key=("k", "customer")),
        _table("spend", {"amount": Role.MEASURE},
               join_key=("k", "product")),              # a different key name
    ])
    assert _result(engine.evaluate(project), "RFM").unlocked is False


def test_tables_connect_transitively_through_a_shared_key(engine):
    """A—B and B—C means A, B and C are all in one joinable group."""
    project = Project("p", [
        _table("a", {"customer_id": Role.IDENTIFIER}, join_key=("k1", "key1")),
        _table("b", {"when": Role.DATE}, join_key=("k1", "key1")),
        _table("c", {"amount": Role.MEASURE}, join_key=("k2", "key1")),
    ])
    assert _result(engine.evaluate(project), "RFM").unlocked is True


# --- unassigned roles don't count -------------------------------------------- #
def test_unassigned_columns_do_not_satisfy_a_template(engine):
    project = Project("p", [_table("sales", {"amount": Role.UNASSIGNED})])
    assert _result(engine.evaluate(project), "Key metrics").unlocked is False
