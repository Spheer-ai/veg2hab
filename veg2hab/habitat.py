import enum
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Union

from veg2hab.criteria import BeperkendCriterium, GeenCriterium, Mozaiekregel
from veg2hab.enums import Kwaliteit, MaybeBoolean
from veg2hab.utils import completely_flatten
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import MatchLevel
from veg2hab.vegetatietypen import VvN as _VvN


@dataclass
class HabitatVoorstel:
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    vegtype: Union[_SBB, _VvN]
    habtype: str
    kwaliteit: Kwaliteit
    idx_opgeschoonde_dt: int
    mits: Optional[BeperkendCriterium]
    mozaiek: Optional[Mozaiekregel]
    match_level: MatchLevel
    percentage: int

    @classmethod
    def H0000_from_info(cls, info: "VegTypeInfo"):
        return cls(
            vegtype=info.VvN[0] if info.VvN else (info.SBB[0] if info.SBB else None),
            habtype="H0000",
            kwaliteit=None,
            idx_opgeschoonde_dt=None,
            mits=GeenCriterium(),
            mozaiek=None,
            match_level=None,
            percentage=info.percentage,
        )

    @classmethod
    def H0000_from_percentage(cls, percentage: int):
        return cls(
            vegtype=None,
            habtype="H0000",
            kwaliteit=None,
            idx_opgeschoonde_dt=None,
            mits=GeenCriterium(),
            mozaiek=None,
            match_level=None,
            percentage=percentage,
        )


class KeuzeStatus(enum.Enum):
    DUIDELIJK = enum.auto()
    GEEN_HABITAT = enum.auto()
    HANDMATIGE_CONTROLE = enum.auto()
    WACHTEN_OP_MOZAIEK = enum.auto()
    MEERDERE_KLOPPENDE_MITSEN = enum.auto()
    # TODO verder opvullen


@dataclass
class HabitatKeuze:
    status: str
    opmerking: str
    debug_info: Optional[str]
    habitatkeuze: List[
        HabitatVoorstel
    ]  # TODO willen we dit nog opschonen?! Baseclass maken zonder mitsen?


def is_criteria_type_present(voorstellen: List[List[HabitatVoorstel]], criteria_type):
    """
    Geeft True als er in de lijst met Criteria eentje van crit_type is
    """
    flat = completely_flatten(voorstellen)
    return any(
        (
            voorstel.mits.is_criteria_type_present(criteria_type)
            if isinstance(voorstel.mits, BeperkendCriterium)
            else False
        )
        for voorstel in flat
    )


def sublist_per_match_level(
    voorstellen: List[HabitatVoorstel],
) -> List[HabitatVoorstel]:
    """
    Splitst een lijst met habitatvoorstellen op in sublijsten per match level
    """
    per_match_level = defaultdict(list)
    for v in voorstellen:
        per_match_level[v.match_level].append(v)

    return [
        per_match_level[key] for key in sorted(per_match_level.keys(), reverse=True)
    ]


def habitatkeuze_obv_mitsen(habitatvoorstellen: List[HabitatVoorstel]) -> HabitatKeuze:
    """
    creeert een habitatkeuze obv ENKEL de mitsen van habitatvoorstellen
    """
    # NOTE: niet vergeten te zorgen dat lege lijsten goed werken
    sublisted_voorstellen = sublist_per_match_level(habitatvoorstellen)

    # PER MATCH LEVEL CHECKEN OP TRUES
    for voorstellen in sublisted_voorstellen:
        # TODO: Voor nu wordt MaybeBoolean.MAYBE en CANNOT_BE_AUTOMATED als simpelweg FALSE gezien
        true_voorstellen = [
            voorstel
            for voorstel in voorstellen
            if voorstel.mits.evaluation == MaybeBoolean.TRUE
        ]

        if len(true_voorstellen) == 1:
            return HabitatKeuze(
                status=KeuzeStatus.DUIDELIJK,
                opmerking=f"Er is een duidelijke keuze. Kloppende mits: {str(true_voorstellen[0].mits)}",
                debug_info="",
                habitatkeuze=true_voorstellen,
            )
        elif len(true_voorstellen) > 1:
            return HabitatKeuze(
                status=KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                opmerking=f"Er zijn meerdere habitatvoorstellen die aan hun mitsen voldoen; Kloppende mitsen: {[str(x.mits) for x in true_voorstellen]}",
                debug_info="",
                habitatkeuze=true_voorstellen,
            )

    return HabitatKeuze(
        status=KeuzeStatus.GEEN_HABITAT,
        opmerking=f"Er is geen habitattype gevonden dat aan de mitsen voldoet. Mitsen waaraan niet is voldaan: {[str(x.mits) for x in completely_flatten(sublisted_voorstellen)]}",
        debug_info="",
        habitatkeuze=[
            HabitatVoorstel.H0000_from_percentage(habitatvoorstellen[0].percentage)
        ],
    )
