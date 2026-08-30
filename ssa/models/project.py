"""A project: the tables uploaded together, with its own id and database file."""

import uuid
from dataclasses import dataclass, field

from ssa.models.dataset_table import DatasetTable


@dataclass
class Project:
    name: str
    tables: list[DatasetTable] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    owner: str = ""
