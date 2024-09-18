import logging
from functools import reduce
from itertools import chain
from operator import and_, or_
from typing import ClassVar, List, Optional, Set, Union

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel, validator
from shapely import wkt
from typing_extensions import Literal

from veg2hab.enums import BodemType, FGRType, LBKType, MaybeBoolean, OBKWaarden


class BeperkendCriterium(BaseModel):
    """
    Superclass voor alle beperkende criteria.
    Subclasses implementeren hun eigen check en non-standaard evaluation methodes.
    Niet-logic sublasses (dus niet EnCriteria, OfCriteria, NietCriterium) moeten een
    cached_evaluation parameter hebben waar het resultaat van check gecached wordt.
    """

    class Config:
        validate_assignment = True

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
        return super().__new__(cls)

    def dict(self, *args, **kwargs):
        """Ik wil type eigenlijk als ClassVar houden, maar dan wordt ie standaard niet mee geserialized.
        Dit is een hack om dat wel voor elkaar te krijgen.
        """
        data = super().dict(*args, **kwargs)
        data["type"] = self.type
        return data

    def json(self, *args, **kwargs):
        """Same here"""
        data = self.dict(*args, **kwargs)
        return self.__config__.json_dumps(data, default=self.__json_encoder__)

    def check(self, row: pd.Series):
        raise NotImplementedError()

    def is_criteria_type_present(self, type):
        return isinstance(self, type)

    def get_info(self) -> Set[str]:
        raise NotImplementedError()

    @property
    def evaluation(self) -> MaybeBoolean:
        """
        Standaard evaluation method
        """
        if self.cached_evaluation is None:
            raise RuntimeError(
                "Evaluation value requested before criteria has been checked"
            )
        return self.cached_evaluation

    def get_format_string(self) -> Optional[str]:
        return None


class GeenCriterium(BeperkendCriterium):
    type: ClassVar[str] = "GeenCriterium"
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        self.cached_evaluation = MaybeBoolean.TRUE

    def __str__(self):
        return "Geen mits (altijd waar)"

    def get_info(self) -> Set[str]:
        return set()


class NietGeautomatiseerdCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietGeautomatiseerd"
    toelichting: str
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        return f"(Niet geautomatiseerd: {self.toelichting})"

    def get_info(self) -> Set[str]:
        return set()


class OverrideCriterium(BeperkendCriterium):
    type: ClassVar[str] = "OverrideCriteria"
    mits: str  # Wordt niet gebruikt voor matching, maar enkel voor __str__
    truth_value: MaybeBoolean
    override_geometry: Optional[List[str]] = None
    truth_value_outside: Optional[MaybeBoolean] = None
    cached_evaluation: Optional[MaybeBoolean] = None

    # We serializen de override_geometry naar een list van strings
    # zodat we later zonder problemen OverrideCriterium kunnen serializen
    @validator("override_geometry", pre=True)
    def check_override_geometry(cls, v):
        if v is None:
            return v

        if isinstance(v, List):
            for i in v:
                assert isinstance(
                    i, str
                ), "override_geometry moet een list van strings (of GeoSeries) zijn"
            return v

        assert isinstance(
            v, gpd.GeoSeries
        ), "override_geometry moet een GeoSeries (of List[str]) zijn"

        return OverrideCriterium.serialize_override_geometry(v)

    @staticmethod
    def serialize_override_geometry(override_geometry):
        return [geom.wkt for geom in override_geometry]

    def get_deserialized_override_geometry(self):
        return gpd.GeoSeries([wkt.loads(geom) for geom in self.override_geometry])

    def check(self, row: pd.Series) -> None:
        assert "geometry" in row, "geometry kolom niet aanwezig"
        assert (self.override_geometry is None) == (
            self.truth_value_outside is None
        ), "Als er een override_geometry is, moet er ook een truth_value_outside zijn (en andersom)"

        if self.override_geometry is None:
            self.cached_evaluation = self.truth_value
            return

        if row.geometry.intersects(self.get_deserialized_override_geometry()).any():
            self.cached_evaluation = self.truth_value
            return

        self.cached_evaluation = ~self.truth_value

    def __str__(self):
        string = "Handmatig overschreven{}: {}"
        return string.format(
            f" (met {self.cached_evaluation.as_letter()})"
            if self.cached_evaluation is not None
            else "",
            self.mits,
        )

    def get_info(self) -> Set[str]:
        return set()


class FGRCriterium(BeperkendCriterium):
    type: ClassVar[str] = "FGRCriterium"
    wanted_fgrtype: FGRType
    actual_fgrtype: Optional[FGRType] = None
    overlap_percentage: float = 0.0
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        assert "fgr" in row, "fgr kolom niet aanwezig"
        assert "fgr_percentage" in row, "fgr_percentage kolom niet aanwezig"
        assert row["fgr"] is not None, "fgr kolom is leeg"

        if pd.isnull(row["fgr"]):
            self.actual_fgrtype = None
            # Er is een NaN als het vlak niet overlapt met een FGR vlak
            self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self.actual_fgrtype = row["fgr"]
        self.overlap_percentage = row["fgr_percentage"]
        self.cached_evaluation = (
            MaybeBoolean.TRUE
            if row["fgr"] == self.wanted_fgrtype
            else MaybeBoolean.FALSE
        )

    def __str__(self):
        string = f"FGR is {self.wanted_fgrtype.value}"
        if self.cached_evaluation is not None:
            string += f" ({self.cached_evaluation.as_letter()})"
        return string

    def get_info(self) -> Set[str]:
        if self.cached_evaluation is None:
            logging.warning(
                "Er wordt om info-strings gevraagd voordat de mits is gecheckt."
            )
            return set()

        if pd.isna(self.actual_fgrtype):
            return {"Dit vlak ligt niet mooi binnen één FGR-vlak."}

        # This string construction is a bit confusing, look at demo_criteria_infos.ipynb to see it in action
        framework = "FGR type is {}{}{} ({})."
        return {
            framework.format(
                "niet " if self.cached_evaluation == MaybeBoolean.FALSE else "",
                self.wanted_fgrtype.value,
                ", maar " + self.actual_fgrtype.value
                if self.cached_evaluation == MaybeBoolean.FALSE
                else "",
                f"{self.overlap_percentage:.1f}%",
            )
        }

    def get_format_string(self):
        return f"FGR is {self.wanted_fgrtype.value}" + " ({})"


class BodemCriterium(BeperkendCriterium):
    type: ClassVar[str] = "BodemCriterium"
    wanted_bodemtype: BodemType
    actual_bodemcode: Optional[List[str]] = None
    overlap_percentage: float = 0.0
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        assert "bodem" in row, "bodem kolom niet aanwezig"
        assert "bodem_percentage" in row, "bodem_percentage kolom niet aanwezig"
        self.actual_bodemcode = (
            None
            if not isinstance(row["bodem"], list) and pd.isna(row["bodem"])
            else row["bodem"]
        )
        self.overlap_percentage = row["bodem_percentage"]
        if self.actual_bodemcode is None:
            # Er is een NaN als het vlak niet binnen een bodemkaartvlak valt
            self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return
        assert isinstance(self.actual_bodemcode, list), "bodem kolom moet een list zijn"

        if len(self.actual_bodemcode) > 1:
            # Vlak heeft meerdere bodemtypen, kunnen we niet automatiseren
            self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self.cached_evaluation = MaybeBoolean.FALSE
        for code in self.actual_bodemcode:
            if code in self.wanted_bodemtype.codes:
                self.cached_evaluation = MaybeBoolean.TRUE
                break

        if (
            self.wanted_bodemtype.enkel_negatieven
            and self.evaluation == MaybeBoolean.TRUE
        ):
            self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        string = f"Bodem is {self.wanted_bodemtype}"
        if self.cached_evaluation is not None:
            string += f" ({self.cached_evaluation.as_letter()})"
        return string

    def get_info(self) -> Set[str]:
        if self.cached_evaluation is None:
            logging.warning(
                "Er wordt om info-strings gevraagd voordat de mits is gecheckt."
            )

        if not isinstance(self.actual_bodemcode, list) and pd.isna(
            self.actual_bodemcode
        ):
            return {"Dit vlak ligt niet binnen een bodemkaartvlak."}

        # This string construction is a bit confusing, look at demo_criteria_infos.ipynb to see it in action
        framework = (
            "Dit is {}{}"
            + str(self.wanted_bodemtype)
            + " want bodemcode "
            + ", ".join(self.actual_bodemcode)
            + f" ({self.overlap_percentage:.1f}%)"
            + "."
        )
        return {
            framework.format(
                "mogelijk "
                if self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                else "",
                "niet " if self.cached_evaluation == MaybeBoolean.FALSE else "",
            )
        }

    def get_format_string(self):
        return f"Bodem is {self.wanted_bodemtype}" + " ({})"


class LBKCriterium(BeperkendCriterium):
    type: ClassVar[str] = "LBKCriterium"
    wanted_lbktype: LBKType
    actual_lbkcode: Optional[str] = None
    overlap_percentage: float = 0.0
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        assert "lbk" in row, "lbk kolom niet aanwezig"
        assert "lbk_percentage" in row, "lbk_percentage kolom niet aanwezig"
        assert row["lbk"] is not None, "lbk kolom is leeg"

        if pd.isna(row["lbk"]):
            self.actual_lbkcode = None
            # Er is een NaN als het vlak niet mooi binnen een LBK vak valt
            self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED
            return

        self.actual_lbkcode = row["lbk"]
        self.overlap_percentage = row["lbk_percentage"]

        self.cached_evaluation = (
            MaybeBoolean.TRUE
            if row["lbk"] in self.wanted_lbktype.codes
            else MaybeBoolean.FALSE
        )

        if self.wanted_lbktype.enkel_negatieven:
            if self.evaluation == MaybeBoolean.TRUE:
                self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

        if self.wanted_lbktype.enkel_positieven:
            if self.evaluation == MaybeBoolean.FALSE:
                self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        string = f"LBK is {self.wanted_lbktype}"
        if self.cached_evaluation is not None:
            string += f" ({self.cached_evaluation.as_letter()})"
        return string

    def get_info(self) -> Set[str]:
        assert (
            self.cached_evaluation is not MaybeBoolean.POSTPONE
        ), "Postpone is not a valid evaluation state for LBKCriterium"
        if self.cached_evaluation is None:
            logging.warning(
                "Er wordt om info-strings gevraagd voordat de mits is gecheckt."
            )

        if pd.isna(self.actual_lbkcode):
            return {"Dit vlak ligt niet mooi binnen één LBK-vak"}

        # This string construction is a bit confusing, look at demo_criteria_infos.ipynb to see it in action
        framework = (
            "Dit is {}{}{}"
            + str(self.wanted_lbktype)
            + " {}LBK code "
            + str(self.actual_lbkcode)
            + f" ({self.overlap_percentage:.1f}%)"
            + "."
        )
        return {
            framework.format(
                "mogelijk "
                if self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                else "",
                "toch "
                if (
                    self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                    and self.wanted_lbktype.enkel_positieven
                )
                else "",
                "niet " if self.cached_evaluation == MaybeBoolean.FALSE else "",
                "ondanks "
                if (
                    self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                    and self.wanted_lbktype.enkel_positieven
                )
                else "want ",
            )
        }

    def get_format_string(self):
        return f"LBK is {self.wanted_lbktype}" + " ({})"


class OudeBossenCriterium(BeperkendCriterium):
    type: ClassVar[str] = "OudeBossenCriterium"
    for_habtype: Literal["H9120", "H9190"]
    actual_OBK: Optional[OBKWaarden] = None
    overlap_percentage: float = 0.0
    cached_evaluation: Optional[MaybeBoolean] = None

    def check(self, row: pd.Series) -> None:
        """
        Als de waarde van de obk kolom None is, dan is het vlak niet binnen een oude bossenkaartvlak,
        dus kunnen we veilig MaybeBoolean.FALSE teruggeven.

        Als de waarde van de obk kolom niet None is, dan is het vlak binnen een oude bossenkaartvlak.
        In dit geval kijken we naar de waarde van de obk kolom voor het for_habtype habitattype (H9120 of H9190).
        Is dit 0, dan is het vlak niet binnen een kwalificerend oud bos, dus geven we MaybeBoolean.FALSE terug.
        Is dit 1 of 2, dan is het aan de gebruiker om te bepalen of het daadwerkelijk binnen een oud bos is,
        dus geven we MaybeBoolean.CANNOT_BE_AUTOMATED terug.
        """
        assert "obk" in row, "obk kolom niet aanwezig"
        assert "obk_percentage" in row, "obk_percentage kolom niet aanwezig"
        assert self.for_habtype in [
            "H9120",
            "H9190",
        ], "for_habtype moet H9120 of H9190 zijn"

        if pd.isna(row["obk"]):
            self.actual_OBK = None
            self.cached_evaluation = MaybeBoolean.FALSE
            return

        self.actual_OBK = row["obk"]
        self.overlap_percentage = row["obk_percentage"]
        value = self.actual_OBK.__getattribute__(self.for_habtype)

        if value == 0:
            self.cached_evaluation = MaybeBoolean.FALSE
            return

        self.cached_evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        string = "Bos ouder dan 1850"
        if self.cached_evaluation is not None:
            string += f" ({self.cached_evaluation.as_letter()})"
        return string

    def get_info(self) -> Set[str]:
        if self.cached_evaluation is None:
            logging.warning(
                "Er wordt om info-strings gevraagd voordat de mits is gecheckt."
            )

        # This string construction is a bit confusing, look at demo_criteria_infos.ipynb to see it in action
        framework = "Dit is {} oud bos, want {}{}."

        return {
            framework.format(
                "mogelijk"
                if self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
                else "geen",
                "niet binnen boskaartvlak"
                if self.actual_OBK is None
                else f"binnen boskaartvlak (H9120: {self.actual_OBK.H9120}, H9190: {self.actual_OBK.H9190})",
                f" ({self.overlap_percentage:.1f}%)"
                if self.actual_OBK is not None
                else "",
            )
        }

    def get_format_string(self):
        return "Bos ouder dan 1850 ({})"


class NietCriterium(BeperkendCriterium):
    type: ClassVar[str] = "NietCriterium"
    sub_criterium: BeperkendCriterium

    def check(self, row: pd.Series) -> None:
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
        format_str = self.sub_criterium.get_format_string()
        if format_str is not None:
            return "niet " + format_str.format(
                (~self.sub_criterium.evaluation).as_letter()
            )
        return f"niet ({self.sub_criterium})"

    def get_info(self) -> Set[str]:
        return self.sub_criterium.get_info()


class OfCriteria(BeperkendCriterium):
    type: ClassVar[str] = "OfCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, row: pd.Series) -> None:
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

    def get_info(self) -> Set[str]:
        return set.union(*[crit.get_info() for crit in self.sub_criteria])


class EnCriteria(BeperkendCriterium):
    type: ClassVar[str] = "EnCriteria"
    sub_criteria: List[BeperkendCriterium]

    def check(self, row: pd.Series) -> None:
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

    def get_info(self) -> Set[str]:
        return set.union(*[crit.get_info() for crit in self.sub_criteria])


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
