"""self-serve analytics (ssa) — core package.

Configurable, transparent self-serve data-analysis engine:
upload CSV -> profile & clean -> semantic config -> progressive-unlock
analyses (KPI / cohort / RFM) -> natural-language query (NL->SQL).

Sub-packages (added step by step in later commits):
    models/    domain objects (Project, DatasetTable, Column, Role)
    db/        thin DuckDB access layer
    services/  data registry, profiling, cleaning, config, unlock, templates, NL query
    llm/       LLM client interface (+ stub used before a real model is wired in)
    utils/     SQL validation, query execution
"""

__version__ = "0.0.1"
