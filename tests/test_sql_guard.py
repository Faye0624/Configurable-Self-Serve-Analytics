"""Tests for the read-only SQL safety validator (NFR-1, covers TC-N1).

The guard is the gate every generated query passes before it runs, so these
tests check both directions: legitimate read-only queries are allowed through,
and a battery of dangerous or malformed queries are all rejected.
"""

import pytest

from ssa.services.sql_guard import SqlGuard, SqlGuardError

ALLOWED_TABLES = {"orders", "customers"}


@pytest.fixture
def guard():
    return SqlGuard()


# --- queries that MUST be allowed ------------------------------------------ #
VALID_QUERIES = [
    'SELECT * FROM orders',
    'SELECT "product_category", SUM("price") AS value FROM orders GROUP BY "product_category"',
    'WITH c AS (SELECT * FROM orders) SELECT COUNT(*) FROM c',
    'SELECT o.price FROM orders AS o JOIN customers USING (id)',
    'SELECT price FROM orders UNION SELECT price FROM orders',
]


@pytest.mark.parametrize("sql", VALID_QUERIES)
def test_valid_read_only_queries_pass(guard, sql):
    result = guard.validate(sql, ALLOWED_TABLES)
    assert isinstance(result, str) and result  # returns the normalised SQL


# --- queries that MUST be rejected ----------------------------------------- #
DANGEROUS_QUERIES = [
    "INSERT INTO orders VALUES (1)",
    "UPDATE orders SET price = 0",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "CREATE TABLE x (a INT)",
    "ALTER TABLE orders ADD COLUMN b INT",
    "SELECT * FROM orders; DROP TABLE orders",   # stacked statements
    "SELECT * FROM secret_table",                # table not in schema
    "COPY orders TO '/tmp/x.csv'",
    "ATTACH 'evil.db'",
    "PRAGMA show_tables",
    "SELECT * INTO evil FROM orders",            # writes a new table
]


@pytest.mark.parametrize("sql", DANGEROUS_QUERIES)
def test_dangerous_queries_are_blocked(guard, sql):
    with pytest.raises(SqlGuardError):
        guard.validate(sql, ALLOWED_TABLES)


# --- specific behaviours ---------------------------------------------------- #
def test_cte_name_is_not_mistaken_for_unknown_table(guard):
    # `temp` is a CTE, not a real table, so it must not trip the allow-list.
    guard.validate('WITH temp AS (SELECT * FROM orders) SELECT * FROM temp', ALLOWED_TABLES)


def test_rejection_message_is_human_readable(guard):
    with pytest.raises(SqlGuardError) as exc:
        guard.validate("DROP TABLE orders", ALLOWED_TABLES)
    assert "read-only" in str(exc.value).lower()


def test_unknown_table_names_the_table(guard):
    with pytest.raises(SqlGuardError) as exc:
        guard.validate("SELECT * FROM secret_table", ALLOWED_TABLES)
    assert "secret_table" in str(exc.value)
