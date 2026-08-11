"""Tests for opt-in cleaning (US3/US4).

The service must never change data on its own: `detect` only reports what could
be fixed, and `apply` changes exactly what the user approved.
"""

import pandas as pd
import pytest

from ssa.services import CleaningService
from ssa.services.cleaning import DROP_DUPLICATES, TRIM_WHITESPACE


@pytest.fixture
def cleaner():
    return CleaningService()


@pytest.fixture
def messy_df():
    """Two fixable problems: padded text values and one duplicate row."""
    df = pd.DataFrame({
        "category": ["  books  ", "toys ", "garden"],
        "price": [10.0, 20.0, 30.0],
    })
    return pd.concat([df, df.iloc[[0]]], ignore_index=True)  # duplicate row


# --- detect: reports problems, changes nothing ----------------------------- #
def test_detect_finds_whitespace_and_duplicates(cleaner, messy_df):
    keys = {o.key for o in cleaner.detect(messy_df)}
    assert keys == {TRIM_WHITESPACE, DROP_DUPLICATES}


def test_detect_does_not_modify_the_data(cleaner, messy_df):
    before = messy_df.copy()
    cleaner.detect(messy_df)
    pd.testing.assert_frame_equal(messy_df, before)


def test_detect_reports_nothing_on_clean_data(cleaner):
    clean = pd.DataFrame({"a": ["x", "y"], "b": [1, 2]})
    assert cleaner.detect(clean) == []


# --- apply: only what the user approved ------------------------------------ #
def test_apply_with_no_approval_leaves_data_untouched(cleaner, messy_df):
    result, actions = cleaner.apply(messy_df, set())
    pd.testing.assert_frame_equal(result, messy_df)
    assert actions == []


def test_apply_trim_only_trims(cleaner, messy_df):
    result, actions = cleaner.apply(messy_df, {TRIM_WHITESPACE})
    assert result["category"].tolist() == ["books", "toys", "garden", "books"]
    assert len(result) == len(messy_df)          # duplicates NOT removed
    assert any("whitespace" in a for a in actions)


def test_apply_dedupe_only_removes_duplicates(cleaner, messy_df):
    result, actions = cleaner.apply(messy_df, {DROP_DUPLICATES})
    assert len(result) == len(messy_df) - 1
    assert result["category"].iloc[0] == "  books  "   # whitespace untouched
    assert any("duplicate" in a for a in actions)


def test_apply_both(cleaner, messy_df):
    result, actions = cleaner.apply(messy_df, {TRIM_WHITESPACE, DROP_DUPLICATES})
    assert len(result) == len(messy_df) - 1
    assert result["category"].tolist() == ["books", "toys", "garden"]
    assert len(actions) == 2


# --- flag_suspicious: report only (US4) ------------------------------------ #
def test_flags_high_missing_column(cleaner):
    df = pd.DataFrame({"a": [1, None, None, None]})
    assert any("missing" in i for i in cleaner.flag_suspicious(df))


def test_flags_mixed_types(cleaner):
    df = pd.DataFrame({"a": [1, "two", 3, "four"]})
    assert any("mixed value types" in i for i in cleaner.flag_suspicious(df))


def test_does_not_flag_normal_data(cleaner):
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": ["w", "x", "y", "z"]})
    assert cleaner.flag_suspicious(df) == []
