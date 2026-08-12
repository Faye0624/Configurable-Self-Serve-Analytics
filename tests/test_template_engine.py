"""Tests for the analysis templates (US12, covers TC-12a/b/c).

These check *correctness of the numbers*, not just that a query runs: the SQL is
generated from the semantic configuration, so a wrong role mapping or a wrong
aggregate would show up here.

The fixture data (see conftest) is four orders:
    c1 buys 10.00 (books, Jan) and 20.00 (toys, Feb)
    c2 buys 30.00 (books, Jan)
    c3 buys 40.00 (garden, Mar)
"""

import pytest

from ssa.models import Project, Role
from ssa.services import TemplateEngine


@pytest.fixture
def engine(db):
    return TemplateEngine(db)


# --- key metrics (TC-12a) ---------------------------------------------------- #
def test_key_metrics_totals_by_dimension(engine, configured_project):
    sql, result = engine.run_key_metrics(configured_project)
    totals = dict(zip(result["product_category"], result["total"]))

    assert totals["books"] == 40.0        # 10 + 30
    assert totals["toys"] == 20.0
    assert totals["garden"] == 40.0
    assert "GROUP BY" in sql


def test_key_metrics_reports_average_and_count(engine, configured_project):
    _, result = engine.run_key_metrics(configured_project)
    books = result[result["product_category"] == "books"].iloc[0]

    assert books["average"] == 20.0       # (10 + 30) / 2
    assert books["n"] == 2


def test_key_metrics_without_a_dimension_gives_one_overall_row(engine, orders_df, db):
    """With only a measure configured, the result is a single summary row."""
    from ssa.services import DataRegistry, SemanticConfigService

    table = DataRegistry(db).add_dataframe("orders", orders_df)
    SemanticConfigService().set_role(table, "price", Role.MEASURE)
    project = Project("p", [table])

    _, result = engine.run_key_metrics(project)

    assert len(result) == 1
    assert result.iloc[0]["total"] == 100.0     # 10 + 20 + 30 + 40
    assert result.iloc[0]["average"] == 25.0
    assert result.iloc[0]["n"] == 4


def test_key_metrics_needs_a_measure(engine, db, orders_df):
    from ssa.services import DataRegistry

    project = Project("p", [DataRegistry(db).add_dataframe("orders", orders_df)])
    with pytest.raises(ValueError, match="measure"):
        engine.run_key_metrics(project)


# --- cohort retention (TC-12b) ------------------------------------------------ #
def test_cohort_groups_customers_by_their_first_month(engine, configured_project):
    _, result = engine.run_cohort(configured_project)
    by_period = {(str(row.cohort_month)[:7], row.period): row.entities
                 for row in result.itertuples()}

    # c1 and c2 both started in January
    assert by_period[("2017-01", 0)] == 2
    # only c1 came back, one month later
    assert by_period[("2017-01", 1)] == 1
    # c3 started in March
    assert by_period[("2017-03", 0)] == 1


def test_cohort_needs_an_identifier_and_a_date(engine, db, orders_df):
    from ssa.services import DataRegistry, SemanticConfigService

    table = DataRegistry(db).add_dataframe("orders", orders_df)
    SemanticConfigService().set_role(table, "price", Role.MEASURE)
    with pytest.raises(ValueError):
        engine.run_cohort(Project("p", [table]))


# --- RFM (TC-12c) ------------------------------------------------------------- #
def test_rfm_computes_recency_frequency_and_monetary(engine, configured_project):
    _, result = engine.run_rfm(configured_project)
    by_entity = {row.entity: row for row in result.itertuples()}

    assert len(result) == 3                       # one row per customer
    assert by_entity["c1"].frequency == 2         # two orders
    assert by_entity["c1"].monetary == 30.0       # 10 + 20
    assert by_entity["c3"].monetary == 40.0
    # recency is measured against the latest date in the data (2017-03-01)
    assert by_entity["c3"].recency_days == 0      # c3 ordered on that date
    assert by_entity["c2"].recency_days > by_entity["c1"].recency_days


def test_rfm_scores_are_within_one_to_five(engine, configured_project):
    _, result = engine.run_rfm(configured_project)
    for score in ("r_score", "f_score", "m_score"):
        assert result[score].between(1, 5).all()


def test_rfm_ranks_recent_customers_higher(engine, configured_project):
    """Recency score should favour the customer who bought most recently."""
    _, result = engine.run_rfm(configured_project)
    scores = {row.entity: row.r_score for row in result.itertuples()}
    assert scores["c3"] > scores["c2"]            # c3 is recent, c2 is stale


def test_rfm_needs_all_three_roles(engine, db, orders_df):
    from ssa.services import DataRegistry, SemanticConfigService

    table = DataRegistry(db).add_dataframe("orders", orders_df)
    SemanticConfigService().set_role(table, "customer_id", Role.IDENTIFIER)
    with pytest.raises(ValueError):
        engine.run_rfm(Project("p", [table]))


# --- transparency: every template hands back its SQL (US16) ------------------- #
@pytest.mark.parametrize("run", ["run_key_metrics", "run_cohort", "run_rfm"])
def test_templates_return_the_sql_they_ran(engine, configured_project, run):
    sql, result = getattr(engine, run)(configured_project)

    assert sql.strip().upper().startswith(("SELECT", "WITH"))
    assert not result.empty
