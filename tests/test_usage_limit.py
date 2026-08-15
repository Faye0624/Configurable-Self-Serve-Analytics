"""Tests for the daily cap on language-model calls.

A deployed instance shares one API key, so the number of model calls per day is
capped. The cap must survive restarts (it is stored in the database) and the
app must degrade with a clear message rather than an error.
"""

import pytest

from ssa.llm import StubLLMClient
from ssa.services import NLQueryEngine, UsageLimiter
from ssa.services.usage_limit import DailyLimitReached


@pytest.fixture
def limiter(db):
    return UsageLimiter(db, daily_limit=3)


def test_starts_with_the_full_allowance(limiter):
    assert limiter.used_today() == 0
    assert limiter.remaining_today() == 3


def test_recording_uses_up_the_allowance(limiter):
    limiter.record()
    limiter.record()
    assert limiter.used_today() == 2
    assert limiter.remaining_today() == 1


def test_check_passes_while_allowance_remains(limiter):
    limiter.record()
    limiter.check()          # should not raise


def test_check_raises_once_the_cap_is_reached(limiter):
    for _ in range(3):
        limiter.record()
    with pytest.raises(DailyLimitReached):
        limiter.check()


def test_the_count_survives_a_restart(db):
    UsageLimiter(db, daily_limit=5).record()
    assert UsageLimiter(db, daily_limit=5).used_today() == 1   # fresh instance


# --- how the query engine behaves at the cap -------------------------------- #
def test_engine_refuses_politely_when_the_cap_is_reached(db, configured_project):
    limiter = UsageLimiter(db, daily_limit=1)
    engine = NLQueryEngine(db, StubLLMClient(), limiter=limiter)

    first = engine.ask(configured_project, "total price by product_category")
    assert first.ok

    second = engine.ask(configured_project, "how many orders")
    assert not second.ok
    assert "daily limit" in second.error       # a message, not a crash


def test_engine_counts_one_call_per_question(db, configured_project):
    limiter = UsageLimiter(db, daily_limit=10)
    engine = NLQueryEngine(db, StubLLMClient(), limiter=limiter)

    engine.ask(configured_project, "total price by product_category")
    engine.ask(configured_project, "how many orders")
    assert limiter.used_today() == 2


def test_replaying_history_does_not_use_the_allowance(db, configured_project):
    """Re-running saved SQL skips the model, so it must not count (US22)."""
    limiter = UsageLimiter(db, daily_limit=10)
    engine = NLQueryEngine(db, StubLLMClient(), limiter=limiter)

    engine.ask(configured_project, "total price by product_category")
    engine.rerun(configured_project, engine.history[0].sql)

    assert limiter.used_today() == 1
