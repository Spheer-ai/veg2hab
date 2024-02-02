import json
from typing import ClassVar, List, Optional

from pydantic import BaseModel

from veg2hab.enums import MaybeBoolean
from veg2hab.fgr import FGRType


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

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        pass


class PlaceholderCriterium(BeperkendCriterium):
    type: ClassVar[str] = "Placeholder"

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        return MaybeBoolean.FALSE

    def is_criteria_type_present(self, type):
        return type == "Placeholder"

class FGRCriterium(BeperkendCriterium):
    type: ClassVar[str] = "FGRCriterium"
    fgrtype: FGRType

    def init(self, fgrtype):
        self.fgrtype = FGRType(fgrtype)

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        pass

    def is_criteria_type_present(self, type):
        return type == "FGRCriterium"

class NietCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietCriterium"
    sub_criterium: BeperkendCriterium

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        return ~self.sub_criterium.check(geometry)
    
    def is_criteria_type_present(self, type):
        return self.sub_criterium.is_criteria_type_present(type)


class OfCriteria(BeperkendCriterium):
    type: ClassVar[str] = "OfCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        # TODO: kloppende MaybeBoolean.MAYBE en MaybeBoolean.CANNOT_BE_AUTOMATED logic
        for crit in self.sub_criteria:
            if crit.check(geometry) == MaybeBoolean.TRUE:
                return MaybeBoolean.TRUE

    def is_criteria_type_present(self, type):
        return any([crit.is_criteria_type_present(type) for crit in self.sub_criteria])


class EnCriteria(BeperkendCriterium):
    type: ClassVar[str] = "EnCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, geometry: "Geometrie") -> MaybeBoolean:
        # TODO: kloppende MaybeBoolean.MAYBE en MaybeBoolean.CANNOT_BE_AUTOMATED logic
        for crit in self.sub_criteria:
            if crit.check(geometry) == MaybeBoolean.FALSE:
                return MaybeBoolean.FALSE
        return MaybeBoolean.TRUE

    def is_criteria_type_present(self, type):
        return any([crit.is_criteria_type_present(type) for crit in self.sub_criteria])


class Mozaiekregel:
    pass
