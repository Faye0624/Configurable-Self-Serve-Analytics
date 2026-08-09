"""Shared pytest fixtures for the test suite.

These build a tiny, fully-configured project (an Olist-like orders table with
roles assigned) so the service/engine tests have realistic input without
touching real data files.
"""

import pandas as pd
import pytest

from ssa.db import Database
from ssa.models import Project, Role
from ssa.services import DataRegistry, ProfilingService, SemanticConfigService


@pytest.fixture
def db():
    """A fresh in-memory DuckDB, closed after each test."""
    database = Database()
    yield database
    database.close()


@pytest.fixture
def orders_df():
    """A small orders table: two orders for c1, one each for c2 and c3."""
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "customer_id": ["c1", "c1", "c2", "c3"],
        "order_date": ["2017-01-05", "2017-02-10", "2017-01-20", "2017-03-01"],
        "product_category": ["books", "toys", "books", "garden"],
        "price": [10.0, 20.0, 30.0, 40.0],
    })


@pytest.fixture
def configured_project(db, orders_df):
    """An orders project stored in the db with roles assigned (id/date/measure/dimension)."""
    registry = DataRegistry(db)
    table = registry.add_dataframe("orders", orders_df)
    ProfilingService().profile(orders_df, table.columns)

    config = SemanticConfigService()
    config.set_role(table, "customer_id", Role.IDENTIFIER)
    config.set_role(table, "order_date", Role.DATE)
    config.set_role(table, "price", Role.MEASURE)
    config.set_role(table, "product_category", Role.DIMENSION)

    project = Project("test")
    project.tables.append(table)
    return project
