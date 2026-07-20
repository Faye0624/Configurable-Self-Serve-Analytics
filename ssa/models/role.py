from enum import Enum


# What a column means, set during configuration. Templates and SQL generation
# key off the role, not the column name. Subclasses str so a Role compares and
# serialises as its value ("measure").
class Role(str, Enum):
    UNASSIGNED = "unassigned"
    IDENTIFIER = "identifier"
    DATE = "date"
    MEASURE = "measure"
    DIMENSION = "dimension"

    def __str__(self) -> str:
        return self.value
