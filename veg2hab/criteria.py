import json
from typing import ClassVar, List, Optional

from pydantic import BaseModel

from veg2hab.enum import MaybeBoolean
from veg2hab.vegkartering import Geometrie


class BeperkendCriterium(BaseModel):
    """
    # TODO
    """

    type: ClassVar[Optional[str]] = None
    _subtypes_: ClassVar[dict] = dict()

    def __init_subclass__(cls):
        # Vul de _subtypes_ dict met alle subclasses
        if cls.type is None:
            raise ValueError(
                "You should specify the `type: ClassVar[str] = 'EnCritera'`"
            )
        cls._subtypes_[cls.type] = cls

    def __new__(cls, *args, **kwargs):
        # Maakt de juiste subclass aan op basis van de type parameter
        if cls == BeperkendCriterium:
            t = kwargs.pop("type")
            return super().__new__(cls._subtypes_[t])
        return super().__new__(cls)  # NOTE: wanneer is het niet een beperkendcriterium?

    def dict(self, *args, **kwargs):
        """Ik wil type eigenlijk als ClassVar houden, maar dan wordt ie standaard niet mee geserialized.
        Dit is een hack om dat wel voor elkaar te krijgen.
        """
        data = super().dict(*args, **kwargs)
        data["type"] = self.type
        return data

    def json(self, *args, **kwargs):
        """Same here"""
        return json.dumps(self.dict(*args, **kwargs))

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class LocatieCriterium(BeperkendCriterium):
    type: ClassVar[str] = "LocatieCriterium"

    def __init__(
        self,
        kaart,  # bijvoorbeeld "FGR"
        kolom,  # bijvoorbeeld "typologie"
        waarde,  # bijvoorbeeld "duinen"
        min_max,
        niet_waarde,
    ):
        pass

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class NietCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietCriterium"
    subCriterium: BeperkendCriterium

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        return ~self.criteria.check(geometry)


class OfCriteria(BeperkendCriterium):
    type: ClassVar[str] = "OfCriteria"
    subCriteria: List[BeperkendCriterium]

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        # TODO: kloppende MaybeBoolean.MAYBE en MaybeBoolean.CANNOT_BE_AUTOMATED logic
        for crit in self.criteria:
            if crit.check(geometry) == MaybeBoolean.TRUE:
                return MaybeBoolean.TRUE


class EnCriteria(BeperkendCriterium):
    type: ClassVar[str] = "EnCriteria"
    subCriteria: List[BeperkendCriterium]

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        # TODO: kloppende MaybeBoolean.MAYBE en MaybeBoolean.CANNOT_BE_AUTOMATED logic
        for crit in self.criteria:
            if crit.check(geometry) == MaybeBoolean.FALSE:
                return MaybeBoolean.FALSE
        return MaybeBoolean.TRUE


class SoortAanwezigCiteria(BeperkendCriterium):
    type: ClassVar[str] = "SoortAanwezigCriterium"
    soorten: List[str]
    min_aantal: int
    max_aantal: Optional[int]

    def __str__(self):
        return f"Minimaal {self.min_aantal} en maximaal {self.max_aantal} van {self.soorten} aanwezig"

    def check(self, geometry: Geometrie) -> MaybeBoolean:
        pass


class Mozaiekregel:
    pass
