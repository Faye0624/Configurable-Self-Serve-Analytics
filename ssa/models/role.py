from enum import Enum


# A column's semantic role, assigned during configuration.
class Role(str, Enum):
    UNASSIGNED = "unassigned"
    IDENTIFIER = "identifier"
    DATE = "date"
    MEASURE = "measure"
    DIMENSION = "dimension"

    def __str__(self) -> str:
        return self.value
