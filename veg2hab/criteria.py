import json
import logging
from functools import reduce
from itertools import chain
from operator import and_, or_
from typing import ClassVar, List, Optional, Set, Union

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel, PrivateAttr

from veg2hab.enums import BodemType, FGRType, LBKType, MaybeBoolean


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

    def get_opm(self) -> Set[str]:
        raise NotImplementedError()

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
        return "Geen mits (altijd waar)"

    def get_opm(self) -> Set[str]:
        return set()


class NietGeautomatiseerdCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietGeautomatiseerd"
    toelichting: str
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        return f"(Niet geautomatiseerd: {self.toelichting})"

    def get_opm(self) -> Set[str]:
        return set()


class FGRCriterium(BeperkendCriterium):
    type: ClassVar[str] = "FGRCriterium"
    wanted_fgrtype: FGRType
    actual_fgrtype: Optional[FGRType] = None
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        assert "fgr" in row, "fgr kolom niet aanwezig"
        assert row["fgr"] is not None, "fgr kolom is leeg"

        self.actual_fgrtype = row["fgr"]

        if pd.isna(row["fgr"]):
            # Er is een NaN als het vlak niet mooi binnen een FGR vlak valt
            self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self._evaluation = (
            MaybeBoolean.TRUE
            if row["fgr"] == self.wanted_fgrtype
            else MaybeBoolean.FALSE
        )

    def __str__(self):
        string = f"FGR is {self.wanted_fgrtype.value}"
        if self._evaluation is not None:
            string += f" ({self._evaluation.as_letter()})"
        return string

    def get_opm(self) -> Set[str]:
        if self._evaluation is None:
            logging.warning(
                "Er wordt om opmerking-strings gevraagd voordat de mits is gecheckt."
            )

        if pd.isna(self.actual_fgrtype):
            return {"Dit vlak ligt niet mooi binnen één FGR-vlak."}
        framework = "FGR type is {}{}{}."
        return {
            framework.format(
                "niet " if self._evaluation == MaybeBoolean.FALSE else "",
                self.wanted_fgrtype.value,
                ", maar " + self.actual_fgrtype.value
                if self._evaluation == MaybeBoolean.FALSE
                else "",
            )
        }

    def get_format_string(self):
        return f"FGR is {self.wanted_fgrtype.value}" + " ({})"


class BodemCriterium(BeperkendCriterium):
    type: ClassVar[str] = "BodemCriterium"
    wanted_bodemtype: BodemType
    actual_bodemcode: List[Optional[str]] = [None]
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        assert "bodem" in row, "bodem kolom niet aanwezig"
        assert isinstance(row["bodem"], list), "bodem kolom moet een list zijn"

        self.actual_bodemcode = row["bodem"]

        if len(row["bodem"]) > 1:
            # Vlak heeft meerdere bodemtypen, kunnen we niet automatiseren
            self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        if pd.isna(row["bodem"]):
            # Er is een NaN als het vlak niet binnen een bodemkaartvlak valt
            self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self._evaluation = MaybeBoolean.FALSE
        for code in row["bodem"]:
            if code in self.wanted_bodemtype.codes:
                self._evaluation = MaybeBoolean.TRUE
                break

        if self.wanted_bodemtype.enkel_negatieven:
            if self.evaluation == MaybeBoolean.TRUE:
                self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        string = f"Bodem is {self.wanted_bodemtype}"
        if self._evaluation is not None:
            string += f" ({self._evaluation.as_letter()})"
        return string

    def get_opm(self) -> Set[str]:
        if self._evaluation is None:
            logging.warning(
                "Er wordt om opmerking-strings gevraagd voordat de mits is gecheckt."
            )

        if len(self.actual_bodemcode) == 1:
            if pd.isna(self.actual_bodemcode[0]):
                return {"Dit vlak ligt niet mooi binnen één bodemkaartvlak."}

        framework = (
            "Dit is {}{}"
            + str(self.wanted_bodemtype)
            + " want bodemcode "
            + ", ".join(self.actual_bodemcode)
            + "."
        )
        return {
            framework.format(
                "mogelijk "
                if self._evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                else "",
                "niet " if self._evaluation == MaybeBoolean.FALSE else "",
            )
        }

    def get_format_string(self):
        return f"Bodem is {self.wanted_bodemtype}" + " ({})"


class LBKCriterium(BeperkendCriterium):
    type: ClassVar[str] = "LBKCriterium"
    wanted_lbktype: LBKType
    actual_lbkcode: Optional[str] = None
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, row: gpd.GeoSeries) -> None:
        assert "lbk" in row, "lbk kolom niet aanwezig"
        assert row["lbk"] is not None, "lbk kolom is leeg"

        self.actual_lbkcode = row["lbk"]

        if pd.isna(row["lbk"]):
            # Er is een NaN als het vlak niet mooi binnen een LBK vak valt
            self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self._evaluation = (
            MaybeBoolean.TRUE
            if row["lbk"] in self.wanted_lbktype.codes
            else MaybeBoolean.FALSE
        )

        if self.wanted_lbktype.enkel_negatieven:
            if self.evaluation == MaybeBoolean.TRUE:
                self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

        if self.wanted_lbktype.enkel_positieven:
            if self.evaluation == MaybeBoolean.FALSE:
                self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        string = f"LBK is {self.wanted_lbktype}"
        if self._evaluation is not None:
            string += f" ({self._evaluation.as_letter()})"
        return string

    def get_opm(self) -> Set[str]:
        assert (
            self._evaluation is not MaybeBoolean.POSTPONE
        ), "Postpone is not a valid evaluation state for LBKCriterium"
        if self._evaluation is None:
            print("test")
            logging.warning(
                "Er wordt om opmerking-strings gevraagd voordat de mits is gecheckt."
            )

        if pd.isna(self.actual_lbkcode):
            return {"Dit vlak ligt niet mooi binnen één LBK-vak"}

        framework = (
            "Dit is {}{}{}"
            + str(self.wanted_lbktype)
            + " {}LBK code "
            + str(self.actual_lbkcode)
            + "."
        )
        return {
            framework.format(
                "mogelijk "
                if self._evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                else "",
                "toch "
                if (
                    self._evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                    and self.wanted_lbktype.enkel_positieven
                )
                else "",
                "niet " if self._evaluation == MaybeBoolean.FALSE else "",
                "ondanks "
                if (
                    self._evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                    and self.wanted_lbktype.enkel_positieven
                )
                else "want ",
            )
        }

    def get_format_string(self):
        return f"LBK is {self.wanted_lbktype}" + " ({})"


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
        # Hier veranderen we "niet FGR is Duinen (F)" naar "niet FGR is Duinen (T)", 
        # want niet false == true
        if type(self.sub_criterium) in [FGRCriterium, BodemCriterium, LBKCriterium]:
            return "niet " + self.sub_criterium.get_format_string().format(
                (~self.sub_criterium.evaluation).as_letter()
            )
        return f"niet {self.sub_criterium}"

    def get_opm(self) -> Set[str]:
        return self.sub_criterium.get_opm()


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

        return reduce(
            or_,
            (crit.evaluation for crit in self.sub_criteria),
            MaybeBoolean.FALSE,
        )

    def __str__(self):
        of_crits = " of ".join(str(crit) for crit in self.sub_criteria)
        return f"({of_crits})"

    def get_opm(self) -> Set[str]:
        return set.union(*[crit.get_opm() for crit in self.sub_criteria])


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

    def get_opm(self) -> Set[str]:
        return set.union(*[crit.get_opm() for crit in self.sub_criteria])


def is_criteria_type_present(
    voorstellen: Union[List[List["HabitatVoorstel"]], List["HabitatVoorstel"]],
    criteria_type: BeperkendCriterium,
) -> bool:
    """
    Geeft True als er in de lijst met voorstellen eentje met een criteria van crit_type is
    Nodig om te bepalen waarmee de gdf verrijkt moet worden (FGR etc)
    """
    # Als we een lijst van lijsten hebben, dan flattenen we die
    if any(isinstance(i, list) for i in voorstellen):
        voorstellen = list(chain.from_iterable(voorstellen))
    return any(
        (
            voorstel.mits.is_criteria_type_present(criteria_type)
            if voorstel.mits is not None
            else False
        )
        for voorstel in voorstellen
    )
