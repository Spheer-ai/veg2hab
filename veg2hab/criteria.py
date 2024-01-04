from typing import List, Optional

from veg2hab.enum import MaybeBoolean
from veg2hab.vegkartering import Geometrie


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


class OfCriteria(BeperkendCriterium):
    def __init__(self, criteria: List[BeperkendCriterium]):
        self.criteria = criteria

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        for crit in self.criteria:
            if crit.check(geometry) == MaybeBoolean.TRUE:
                return MaybeBoolean.TRUE


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


class Mozaiekregel:
    pass
