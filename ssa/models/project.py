from dataclasses import dataclass, field

from ssa.models.dataset_table import DatasetTable


# A project groups the tables a user uploads and configures together.
@dataclass
class Project:
    name: str
    tables: list[DatasetTable] = field(default_factory=list)
