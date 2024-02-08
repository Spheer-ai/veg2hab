# import geopandas as gpd


from enum import Enum


class MaybeBoolean(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MAYBE = "MAYBE"  # Used for when evaluation needs to be postponed
    CANNOT_BE_AUTOMATED = "CANNOT_BE_AUTOMATED"  # Used when manual action is required

    def __invert__(self):
        if self == MaybeBoolean.TRUE:
            return MaybeBoolean.FALSE
        elif self == MaybeBoolean.FALSE:
            return MaybeBoolean.TRUE
        else:
            return self


class Kwaliteit(Enum):
    GOED = "Goed"
    MATIG = "Matig"

    @classmethod
    def from_letter(cls, letter: str):
        if letter == "G":
            return cls.GOED
        elif letter == "M":
            return cls.MATIG
        else:
            raise ValueError("Letter moet G of M zijn")

    def as_letter(self):
        if self == Kwaliteit.GOED:
            return "G"
        elif self == Kwaliteit.MATIG:
            return "M"
        else:
            raise ValueError("GoedMatig is niet Goed of Matig")
