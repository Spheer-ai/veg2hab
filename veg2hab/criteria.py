import json
from functools import reduce
from operator import and_, or_
from typing import ClassVar, List, Optional

import geopandas as gpd
from pydantic import BaseModel, PrivateAttr

from veg2hab.enums import MaybeBoolean
from veg2hab.fgr import FGRType


class BeperkendCriterium(BaseModel):
    """
    Superclass voor alle beperkende criteria.
    Subclasses implementeren hun eigen check en non-standaard evaluation methodes.
    Niet-logic sublasses (dus niet EnCriteria, OfCriteria, NietCriterium) moeten een
    _evaluation parameter hebben waar het resultaat van check gecached wordt.
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
        return super().__new__(
            cls
        )  # NOTE: wanneer is het niet een beperkendcriterium? TODO Mark vragen

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

    def check(self, row: gpd.GeoSeries):
        raise NotImplementedError()

    def is_criteria_type_present(self, type):
        return isinstance(self, type)

    @property
    def evaluation(self) -> MaybeBoolean:
        """
        Standaard evaluation method
        """
        if self._evaluation is None:
            raise RuntimeError(
                "Evaluation value requested before criteria has been checked"
            )
        return self._evaluation


class GeenCriterium(BeperkendCriterium):
    type: ClassVar[str] = "GeenCriterium"
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        self._evaluation = MaybeBoolean.TRUE

    def __str__(self):
        return "geen mits (altijd waar)"


class PlaceholderCriterium(BeperkendCriterium):
    type: ClassVar[str] = "Placeholder"
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        return "placeholder"


class FGRCriterium(BeperkendCriterium):
    type: ClassVar[str] = "FGRCriterium"
    fgrtype: FGRType
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        assert "fgr" in row, "fgr kolom niet aanwezig"
        assert row["fgr"] is not None, "fgr kolom is leeg"
        self._evaluation = (
            MaybeBoolean.TRUE if row["fgr"] == self.fgrtype else MaybeBoolean.FALSE
        )

    def __str__(self):
        return f"FGR is {self.fgrtype.value}"


class NietCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietCriterium"
    sub_criterium: BeperkendCriterium

    def check(self, row: gpd.GeoSeries) -> None:
        self.sub_criterium.check(row)

    def is_criteria_type_present(self, type) -> bool:
        return self.sub_criterium.is_criteria_type_present(type) or isinstance(
            self, type
        )

    @property
    def evaluation(self) -> MaybeBoolean:
        return ~self.sub_criterium.evaluation

    def __str__(self):
        return f"niet {self.sub_criterium}"


class OfCriteria(BeperkendCriterium):
    type: ClassVar[str] = "OfCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, row: gpd.GeoSeries) -> None:
        for crit in self.sub_criteria:
            crit.check(row)

    def is_criteria_type_present(self, type) -> bool:
        return any(
            crit.is_criteria_type_present(type) for crit in self.sub_criteria
        ) or isinstance(self, type)

    @property
    def evaluation(self) -> MaybeBoolean:
        assert len(self.sub_criteria) > 0, "OrCriteria zonder subcriteria"
        test = reduce(
            lambda x, y: x | y,
            (crit.evaluation for crit in self.sub_criteria),
            MaybeBoolean.FALSE,
        )
        test2 = reduce(
            or_,
            (crit.evaluation for crit in self.sub_criteria),
            MaybeBoolean.FALSE,
        )
        assert test == test2
        return reduce(
            lambda x, y: x | y,
            (crit.evaluation for crit in self.sub_criteria),
            MaybeBoolean.FALSE,
        )

    def __str__(self):
        of_crits = " of ".join(str(crit) for crit in self.sub_criteria)
        return f"({of_crits})"


class EnCriteria(BeperkendCriterium):
    type: ClassVar[str] = "EnCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, row: gpd.GeoSeries) -> None:
        for crit in self.sub_criteria:
            crit.check(row)

    def is_criteria_type_present(self, type) -> bool:
        return any(
            crit.is_criteria_type_present(type) for crit in self.sub_criteria
        ) or isinstance(self, type)

    @property
    def evaluation(self) -> MaybeBoolean:
        assert len(self.sub_criteria) > 0, "EnCriteria zonder subcriteria"
        return reduce(
            and_,
            (crit.evaluation for crit in self.sub_criteria),
            MaybeBoolean.TRUE,
        )

    def __str__(self):
        en_crits = " en ".join(str(crit) for crit in self.sub_criteria)
        return f"({en_crits})"


