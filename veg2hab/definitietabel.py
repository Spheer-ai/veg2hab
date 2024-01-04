from typing import List, Optional, Sequence
import pandas as pd
from enum import Enum
from dataclasses import dataclass

# import geopandas as gpd


class MaybeBoolean(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MAYBE = "MAYBE"
    CANNOT_BE_AUTOMATED = "CANNOT_BE_AUTOMATED"


class GoedMatig(Enum):
    GOED = "Goed"
    MATIG = "Matig"


class Geometrie:
    """Een shape uit de vegetatiekartering.
    Deze bevat of een VvN of een SBB code en een geometrie.
    """

    # data: gpd.Dataframe


class BeperkendCriterium:  # TODO abstract base class
    """BeperkendCriteria Interface
    Bevat een of meerdere condities waaraan een geometrie hoort
    te voldoen, voordat het klasificeert als een bepaalt habitattype
    """

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class LocatieCritera(BeperkendCriterium):
    def __init__(
        self,
        kaart,  # bijvoorbeeld "FGR"
        kolom,  # bijvoorbeeld "typolgie"
        waarde,  # bijvoorbeeld "duinen"
        min_max,
        niet_waarde,
    ):
        pass

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class SoortAanwezigCiteria(BeperkendCriterium):
    def __init__(
        self,
        soorten: List[str],
        min_aantal: int = 1,
        max_aantal: Optional[int] = None,
    ):
        self.soorten = soorten
        self.min_aantal = min_aantal
        self.max_aantal = max_aantal

    def __str__(self):
        return f"Minimaal {self.min_aantal} en maximaal {self.max_aantal} van {self.soorten} aanwezig"

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class OfCriteria(BeperkendCriterium):
    def __init__(self, criteria: List[BeperkendCriterium]):
        self.criteria = criteria

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        for crit in self.criteria:
            if crit.check(geometry) == MaybeBoolean.TRUE:
                return MaybeBoolean.TRUE


class Mozaiekregel:
    pass


@dataclass
class DefinitieRowItem:
    row_idx: int
    VvN: Optional[str]  # enum?
    SBB: Optional[str]  # enum?
    HABCODE: str  # enum?
    Kwaliteit: GoedMatig
    mits: BeperkendCriterium
    mozaiek: MozaiekRegel

    def __post_init__(self):
        if (self.VvN is None) != (self.SBB is None):
            raise ValueError("Precies een van VvN of SBB moet een waarde hebben")


class DefinitieTabel:
    data: List[DefinitieRowItem]

    def __init__(self):
        pass

    def from_pandas(self, df):
        self.validate(df)
        pass

    @staticmethod
    def validate(self):
        pass
