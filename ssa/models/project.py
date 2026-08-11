import uuid
from dataclasses import dataclass, field

from ssa.models.dataset_table import DatasetTable


# A project groups the tables a user uploads and configures together.
# Each project belongs to a user and owns its own database file, so two
# projects can hold same-named tables without colliding.
@dataclass
class Project:
    name: str
    tables: list[DatasetTable] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    owner: str = ""
