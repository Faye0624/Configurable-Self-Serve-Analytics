from dataclasses import dataclass, field

from ssa.models.role import Role


# One column of a dataset table. each column of the table will create a new column object
@dataclass
class Column:
    # dataclass is init, repr(decide what print will show), eq(decide two object is equal or not)
    name: str
    data_type: str
    # Set during configuration.
    role: Role = Role.UNASSIGNED
    is_join_key: bool = False
    key_name: str = ""
    # Filled in by profiling.
    null_pct: float = 0.0
    distinct_count: int = 0
    # create a new list[] for every column object rather than share one list[]
    sample: list = field(default_factory=list)
