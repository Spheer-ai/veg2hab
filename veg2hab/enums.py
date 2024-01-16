# import geopandas as gpd


from enum import Enum


class MaybeBoolean(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MAYBE = "MAYBE"
    CANNOT_BE_AUTOMATED = "CANNOT_BE_AUTOMATED"


class GoedMatig(Enum):
    GOED = "Goed"
    MATIG = "Matig"
