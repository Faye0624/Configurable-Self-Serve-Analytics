"""Tests for per-column profiling (US2, covers TC-2)."""

import numpy as np
import pandas as pd
import pytest

from ssa.models import Column
from ssa.services import ProfilingService


@pytest.fixture
def profiler():
    return ProfilingService()


def _profile(profiler, df):
    columns = [Column(name, str(df[name].dtype)) for name in df.columns]
    profiler.profile(df, columns)
    return {c.name: c for c in columns}


def test_missing_percentage_is_calculated(profiler):
    df = pd.DataFrame({"complete": [1, 2, 3, 4], "half": [1, None, 3, None]})
    profiled = _profile(profiler, df)

    assert profiled["complete"].null_pct == 0.0
    assert profiled["half"].null_pct == 50.0


def test_distinct_count_ignores_missing_values(profiler):
    df = pd.DataFrame({"letters": ["a", "b", "b", None]})
    assert _profile(profiler, df)["letters"].distinct_count == 2


def test_sample_values_are_collected(profiler):
    df = pd.DataFrame({"letters": list("abcdefgh")})
    sample = _profile(profiler, df)["letters"].sample

    assert len(sample) == ProfilingService.SAMPLE_SIZE
    assert set(sample) <= set("abcdefgh")


def test_sample_excludes_missing_values(profiler):
    df = pd.DataFrame({"gaps": [None, "x", None, "y"]})
    assert _profile(profiler, df)["gaps"].sample == ["x", "y"]


def test_profiles_a_realistic_table(profiler, orders_df):
    profiled = _profile(profiler, orders_df)

    assert profiled["customer_id"].distinct_count == 3      # c1, c2, c3
    assert profiled["order_id"].distinct_count == len(orders_df)
    assert all(c.null_pct == 0.0 for c in profiled.values())


def test_empty_table_does_not_break_profiling(profiler):
    df = pd.DataFrame({"a": pd.Series(dtype="float64")})
    profiled = _profile(profiler, df)

    assert profiled["a"].null_pct == 0.0
    assert profiled["a"].distinct_count == 0
    assert profiled["a"].sample == []
