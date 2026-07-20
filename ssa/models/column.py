from dataclasses import dataclass

from ssa.models.role import Role


# One column of a dataset table.
@dataclass
class Column:
    name: str
    data_type: str
    role: Role = Role.UNASSIGNED
