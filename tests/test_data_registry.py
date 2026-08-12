"""Tests for loading uploaded data into the database (US1, covers TC-1)."""

import pandas as pd
import pytest

from ssa.services import DataRegistry, safe_table_name


@pytest.fixture
def registry(db):
    return DataRegistry(db)


# --- table naming ---------------------------------------------------------- #
@pytest.mark.parametrize("filename, expected", [
    ("orders.csv", "orders"),
    ("Orders 2024.csv", "orders_2024"),
    ("my-file.name.csv", "my_file_name"),
    ("/tmp/path/to/Sales Data.csv", "sales_data"),
    ("__weird__.csv", "weird"),
])
def test_filenames_become_safe_table_names(filename, expected):
    assert safe_table_name(filename) == expected


# --- registering a frame ---------------------------------------------------- #
def test_dataframe_is_stored_and_registered(registry, db, orders_df):
    table = registry.add_dataframe("orders", orders_df, source_file="orders.csv")

    assert table.name == "orders"
    assert table.row_count == len(orders_df)
    assert table.source_file == "orders.csv"
    assert [c.name for c in table.columns] == list(orders_df.columns)
    assert "orders" in db.list_tables()
    assert db.query("SELECT COUNT(*) AS n FROM orders").iloc[0]["n"] == len(orders_df)


def test_column_types_are_captured(registry, orders_df):
    table = registry.add_dataframe("orders", orders_df)
    types = {c.name: c.data_type for c in table.columns}
    assert "int" in types["order_id"]
    assert "float" in types["price"]
    assert types["customer_id"] == "object"


def test_tables_accumulate_so_data_can_arrive_piece_by_piece(registry, orders_df):
    registry.add_dataframe("orders", orders_df)
    registry.add_dataframe("customers", pd.DataFrame({"customer_id": ["c1", "c2"]}))

    assert set(registry.tables) == {"orders", "customers"}


def test_re_uploading_replaces_the_previous_table(registry, db, orders_df):
    registry.add_dataframe("orders", orders_df)
    registry.add_dataframe("orders", orders_df.head(2))   # a corrected upload

    assert registry.tables["orders"].row_count == 2
    assert db.query("SELECT COUNT(*) AS n FROM orders").iloc[0]["n"] == 2


# --- registering from a CSV file -------------------------------------------- #
def test_add_csv_reads_the_file_and_names_the_table(registry, db, orders_df, tmp_path):
    path = tmp_path / "Olist Orders.csv"
    orders_df.to_csv(path, index=False)

    table = registry.add_csv(str(path))

    assert table.name == "olist_orders"          # derived from the filename
    assert table.source_file == "Olist Orders.csv"
    assert table.row_count == len(orders_df)
    assert "olist_orders" in db.list_tables()
