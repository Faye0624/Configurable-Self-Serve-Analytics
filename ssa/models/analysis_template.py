"""Each analysis declares the roles it needs — the unlock rules as data."""

from dataclasses import dataclass

from ssa.models.role import Role


@dataclass(frozen=True)
class AnalysisTemplate:
    name: str
    # What roles are needed to run the model
    required_roles: frozenset[Role] 
    # how to explain to the user (only show when models are locked)
    description: str = ""


#The standard analyses the tool ships with.
#-----
#The descriptions say what each analysis tells you, in the words someone would
#use to ask for it — no "measure", no "entities". Those are configuration terms
#and belong in the lock message, where the point is which column to go and set.
STANDARD_TEMPLATES = [
    AnalysisTemplate(
        "Key metrics", frozenset({Role.MEASURE}),
        "Totals, averages and counts — total sales, average order value, and so on."),
    AnalysisTemplate(
        "Cohort / retention", frozenset({Role.IDENTIFIER, Role.DATE}),
        "How many of each month's newcomers keep coming back later."),
    AnalysisTemplate(
        "RFM", frozenset({Role.IDENTIFIER, Role.DATE, Role.MEASURE}),
        "Groups customers by how recently they bought, how often, and how much."),
]
