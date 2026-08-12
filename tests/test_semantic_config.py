"""Tests for the no-code semantic configuration (US6-US8, covers TC-6..8).

The configuration layer is what makes the engine domain-independent: the user
declares what each column *means* (its role) and which columns link tables
together, and everything downstream is driven by that.
"""

import pytest

from ssa.models import Column, DatasetTable, Role
from ssa.services import SemanticConfigService


@pytest.fixture
def config():
    return SemanticConfigService()


@pytest.fixture
def orders_table():
    return DatasetTable("orders", [
        Column("order_id", "int64"),
        Column("customer_id", "object"),
        Column("order_date", "object"),
        Column("product_category", "object"),
        Column("price", "float64"),
    ])


def _col(table, name):
    return next(c for c in table.columns if c.name == name)


# --- assigning roles (US6) --------------------------------------------------- #
def test_set_role_assigns_the_role(config, orders_table):
    config.set_role(orders_table, "price", Role.MEASURE)
    assert _col(orders_table, "price").role == Role.MEASURE


def test_role_can_be_changed_again(config, orders_table):
    config.set_role(orders_table, "price", Role.MEASURE)
    config.set_role(orders_table, "price", Role.DIMENSION)
    assert _col(orders_table, "price").role == Role.DIMENSION


def test_unknown_column_raises_a_clear_error(config, orders_table):
    with pytest.raises(KeyError) as exc:
        config.set_role(orders_table, "no_such_column", Role.MEASURE)
    assert "no_such_column" in str(exc.value)


# --- join keys (US7) --------------------------------------------------------- #
def test_join_key_defaults_to_the_column_name(config, orders_table):
    config.set_join_key(orders_table, "order_id")
    column = _col(orders_table, "order_id")
    assert column.is_join_key is True
    assert column.key_name == "order_id"


def test_join_key_can_use_a_shared_name_across_tables(config, orders_table):
    config.set_join_key(orders_table, "customer_id", key_name="customer")
    assert _col(orders_table, "customer_id").key_name == "customer"


def test_clearing_a_join_key_resets_it(config, orders_table):
    config.set_join_key(orders_table, "order_id")
    config.clear_join_key(orders_table, "order_id")
    column = _col(orders_table, "order_id")
    assert column.is_join_key is False
    assert column.key_name == ""


# --- automatic suggestions (US8) --------------------------------------------- #
def test_suggest_prefills_roles_from_names_and_types(config, orders_table):
    config.suggest(orders_table)
    roles = {c.name: c.role for c in orders_table.columns}

    assert roles["customer_id"] == Role.IDENTIFIER      # id + a "customer" hint
    assert roles["order_date"] == Role.DATE             # name contains "date"
    assert roles["price"] == Role.MEASURE               # numeric
    assert roles["product_category"] == Role.DIMENSION  # text, no hints


def test_suggest_marks_id_columns_as_join_keys(config, orders_table):
    config.suggest(orders_table)
    assert _col(orders_table, "order_id").is_join_key is True
    assert _col(orders_table, "customer_id").is_join_key is True
    assert _col(orders_table, "price").is_join_key is False


def test_suggest_leaves_a_plain_id_without_an_analysis_role(config, orders_table):
    """order_id links rows; it is not something you analyse, so it stays unassigned."""
    config.suggest(orders_table)
    assert _col(orders_table, "order_id").role == Role.UNASSIGNED


def test_suggestions_can_be_overridden_by_the_user(config, orders_table):
    config.suggest(orders_table)
    config.set_role(orders_table, "product_category", Role.IDENTIFIER)
    assert _col(orders_table, "product_category").role == Role.IDENTIFIER
