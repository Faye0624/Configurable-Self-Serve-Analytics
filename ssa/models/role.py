from enum import Enum


# A column's semantic role, assigned during configuration.
class Role(str, Enum):  
    UNASSIGNED = "unassigned" #user and db will see
    IDENTIFIER = "identifier"
    DATE = "date"
    MEASURE = "measure"
    DIMENSION = "dimension"
#  what print will show
    def __str__(self) -> str:
        return self.value
