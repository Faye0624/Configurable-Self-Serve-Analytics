"""The offline stub: two defects found by the NL benchmark (evaluation/), fixed and pinned."""

from ssa.llm import StubLLMClient
from ssa.llm.schema import Schema, SchemaColumn, SchemaTable


def _two_tables() -> Schema:
    # orders has no measure; order_items does — the study dataset's shape.
    return Schema((
        SchemaTable("orders", (
            SchemaColumn("order_id", "object", "unassigned"),
            SchemaColumn("customer_id", "object", "identifier"),
            SchemaColumn("order_date", "object", "date"),
        )),
        SchemaTable("order_items", (
            SchemaColumn("order_id", "object", "unassigned"),
            SchemaColumn("product_category", "object", "dimension"),
            SchemaColumn("price", "float64", "measure"),
        )),
    ))


# An aggregation with no table named used to bind to the first table, which has
# no measure, and emit SUM("None").
def test_aggregation_moves_to_a_table_that_has_a_measure():
    sql = StubLLMClient().generate_sql("what is the total revenue", _two_tables())
    assert '"None"' not in sql
    assert 'SUM("price")' in sql and '"order_items"' in sql


# "top N" on an unrecognised question appended a second LIMIT to the preview.
def test_top_n_does_not_produce_two_limit_clauses():
    sql = StubLLMClient().generate_sql("top 5 anything at all", _two_tables())
    assert sql.upper().count("LIMIT") == 1
