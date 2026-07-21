from dataclasses import dataclass, field

from ssa.models.role import Role


# One column of a dataset table.
@dataclass
class Column:
    name: str
    data_type: str
    # Set during configuration.
    role: Role = Role.UNASSIGNED
    is_join_key: bool = False
    key_name: str = ""
    # Filled in by profiling.
    null_pct: float = 0.0
    distinct_count: int = 0
    sample: list = field(default_factory=list)
