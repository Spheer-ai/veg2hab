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


class GoedMatig(Enum):
    GOED = "Goed"
    MATIG = "Matig"
