from dataclasses import dataclass, field

from ssa.models.column import Column


# One uploaded table and its columns.
@dataclass
class DatasetTable:
    name: str
    columns: list[Column] = field(default_factory=list)
    source_file: str = ""
    row_count: int = 0
