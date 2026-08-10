"""Tests for the NL->SQL engine (US15, US17, US22).

Uses the offline StubLLMClient so the tests are deterministic and need no API
key. Covers: a question becomes runnable SQL, a saved query replays without the
model, dangerous model output is rejected, and the query log persists across a
(simulated) restart.
"""

import pytest

from ssa.db import Database
from ssa.llm import StubLLMClient
from ssa.services import NLQueryEngine


@pytest.fixture
def engine(db):
    return NLQueryEngine(db, StubLLMClient())


# US15: a natural-language question turns into a runnable query.
def test_ask_generates_sql_and_runs(engine, configured_project):
    result = engine.ask(configured_project, "total price by product_category")
    assert result.ok
    assert "GROUP BY" in result.sql
    assert len(engine.history) == 1


# US22: replay executes the stored SQL directly (no model call) with same result.
def test_rerun_uses_stored_sql(engine, configured_project):
    first = engine.ask(configured_project, "how many orders")
    replay = engine.rerun(configured_project, engine.history[0].sql)
    assert replay.ok and replay.from_cache
    assert replay.sql == first.sql


# US17 / NFR-1: unsafe model output is rejected, returned as a message not a crash.
def test_dangerous_model_output_is_rejected(db, configured_project):
    class Evil(StubLLMClient):
        def generate_sql(self, question, schema):
            return "DROP TABLE orders"

    result = NLQueryEngine(db, Evil()).ask(configured_project, "wipe it")
    assert not result.ok
    assert "unsafe" in result.error


# US22: history is durable — a fresh engine on the same history DB reloads it.
def test_history_persists_across_restart(db, configured_project, tmp_path):
    history_path = str(tmp_path / "history.duckdb")

    engine = NLQueryEngine(db, StubLLMClient(), history_db=Database(history_path))
    result = engine.ask(configured_project, "total price by product_category")
    assert len(engine.history) == 1

    reopened = NLQueryEngine(db, StubLLMClient(), history_db=Database(history_path))
    assert len(reopened.history) == 1
    assert reopened.history[0].sql == result.sql
