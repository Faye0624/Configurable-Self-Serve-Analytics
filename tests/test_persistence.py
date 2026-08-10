"""Tests for project persistence — data and config survive a restart."""

from ssa.db import Database
from ssa.models import Project, Role
from ssa.services import (DataRegistry, ProfilingService, SemanticConfigService,
                          load_project, save_project)


def test_project_and_data_persist(tmp_path, orders_df):
    path = str(tmp_path / "workspace.duckdb")

    # Session 1: upload, configure, save.
    db = Database(path)
    reg = DataRegistry(db)
    table = reg.add_dataframe("orders", orders_df, source_file="orders.csv")
    ProfilingService().profile(orders_df, table.columns)
    cfg = SemanticConfigService()
    cfg.set_role(table, "customer_id", Role.IDENTIFIER)
    cfg.set_role(table, "price", Role.MEASURE)
    cfg.set_join_key(table, "order_id")
    project = Project("demo")
    project.tables.append(table)
    save_project(db, project)
    db.close()

    # Session 2: a fresh connection to the same file restores config + data.
    db2 = Database(path)
    restored = load_project(db2)
    assert restored is not None
    assert [t.name for t in restored.tables] == ["orders"]

    cols = {c.name: c for c in restored.tables[0].columns}
    assert cols["customer_id"].role == Role.IDENTIFIER
    assert cols["price"].role == Role.MEASURE
    assert cols["order_id"].is_join_key is True

    # the data itself is still there and queryable
    assert "orders" in db2.list_tables()
    assert db2.query("SELECT COUNT(*) AS n FROM orders").iloc[0]["n"] == len(orders_df)


def test_load_returns_none_on_fresh_db(tmp_path):
    assert load_project(Database(str(tmp_path / "empty.duckdb"))) is None
