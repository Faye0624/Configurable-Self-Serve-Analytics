# Domain model: plain data objects (Project, DatasetTable, Column, Role).
from ssa.models.role import Role
from ssa.models.column import Column
from ssa.models.dataset_table import DatasetTable
from ssa.models.project import Project

__all__ = ["Role", "Column", "DatasetTable", "Project"]
