from dataclasses import dataclass

from ssa.models.role import Role


# A pre-built analysis and the column roles it needs before it can run.
@dataclass(frozen=True)
class AnalysisTemplate:
    name: str
    required_roles: frozenset[Role]
    description: str = ""


# The standard analyses the tool ships with.
STANDARD_TEMPLATES = [
    AnalysisTemplate(
        "Key metrics", frozenset({Role.MEASURE}),
        "Totals, averages and counts of a measure (e.g. total sales, average order value)."),
    AnalysisTemplate(
        "Cohort / retention", frozenset({Role.IDENTIFIER, Role.DATE}),
        "How groups of entities keep coming back over time."),
    AnalysisTemplate(
        "RFM", frozenset({Role.IDENTIFIER, Role.DATE, Role.MEASURE}),
        "Recency / Frequency / Monetary customer segmentation."),
]
