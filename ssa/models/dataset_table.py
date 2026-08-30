"""One uploaded table and its columns."""

from dataclasses import dataclass, field

from ssa.models.column import Column


@dataclass
class DatasetTable:
    name: str
    columns: list[Column] = field(default_factory=list)
    source_file: str = ""
    row_count: int = 0
