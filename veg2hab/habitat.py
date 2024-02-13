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

    # NOTE: Deze class is wel heel vol nu, maar veel van deze info is nodig om een duidelijke output te geven met voldoende debug info
    onderbouwend_vegtype: Union[_SBB, _VvN]
    vegtype_in_dt: Union[_SBB, _VvN]
    vegtypeinfo: "VegTypeInfo"
    habtype: str
    kwaliteit: Kwaliteit
    idx_opgeschoonde_dt: int
    idx_in_dt: int
    mits: Optional[BeperkendCriterium]
    mozaiek: Optional[Mozaiekregel]
    match_level: MatchLevel
    percentage: int

    @classmethod
    def H0000_vegtype_not_in_dt(cls, info: "VegTypeInfo"):
        return cls(
            onderbouwend_vegtype=info.VvN[0]
            if info.VvN
            else (info.SBB[0] if info.SBB else None),
            vegtype_in_dt=None,
            vegtypeinfo=info,
            habtype="H0000",
            kwaliteit=None,
            idx_opgeschoonde_dt=None,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=None,
            match_level=MatchLevel.NO_MATCH,
            percentage=info.percentage,
        )


class KeuzeStatus(enum.Enum):
    # 1 Habitatvoorstel met kloppende mits
    DUIDELIJK = enum.auto()

    # Geen habitatvoorstel met kloppende mits, dus H0000
    GEEN_KLOPPENDE_MITSEN = enum.auto()

    # Vegtypen niet in deftabel gevonden, dus H0000
    VEGTYPEN_NIET_IN_DEFTABEL = enum.auto()

    # Meerdere even specifieke habitatvoorstellen met kloppende mitsen
    MEERDERE_KLOPPENDE_MITSEN = enum.auto()

    HANDMATIGE_CONTROLE = enum.auto()
    WACHTEN_OP_MOZAIEK = enum.auto()


@dataclass
class HabitatKeuze:
    status: str
    opmerking: str
    debug_info: Optional[str]
    habitatvoorstellen: List[HabitatVoorstel]
    # TODO willen we dit nog opschonen?! Baseclass maken zonder mitsen?


def is_criteria_type_present(voorstellen: List[List[HabitatVoorstel]], criteria_type):
    """
    Geeft True als er in de lijst met Criteria eentje van crit_type is
    Nodig om te bepalen waarmee de gdf verrijkt moet worden (FGR etc)
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


def rank_habitatkeuzes(keuze: HabitatKeuze) -> tuple:
    """
    Returned een tuple voor het sorteren van een lijst habitatkeuzes voor in de outputtabel
    We zetten eerst alle H0000 achteraan, daarna sorteren we op percentage, daarna op kwaliteit
    """
    voorgestelde_habtypen = [voorstel.habtype for voorstel in keuze.habitatvoorstellen]
    alleen_H0000 = all(habtype == "H0000" for habtype in voorgestelde_habtypen)

    percentage = keuze.habitatvoorstellen[0].percentage

    voorgestelde_kwaliteiten = [voorstel.kwaliteit for voorstel in keuze.habitatvoorstellen]
    matig_kwaliteit = voorgestelde_kwaliteiten == [Kwaliteit.MATIG]

    return (alleen_H0000, 100 - percentage, matig_kwaliteit)


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
    Creeert een habitatkeuze obv ENKEL de mitsen van habitatvoorstellen
    """
    assert len(habitatvoorstellen) > 0, "Er zijn geen habitatvoorstellen"

    # Als er maar 1 habitatvoorstel is en dat is H0000, dan zat geen van de vegtypen in de deftabel
    if len(habitatvoorstellen) == 1 and habitatvoorstellen[0].habtype == "H0000":
        return HabitatKeuze(
            status=KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            opmerking="",
            debug_info=f"{str(habitatvoorstellen[0].vegtypeinfo)}",
            habitatvoorstellen=habitatvoorstellen,
        )

    sublisted_voorstellen = sublist_per_match_level(habitatvoorstellen)

    # Per MatchLevel checken of er kloppende mitsen zijn
    for voorstellen in sublisted_voorstellen:
        # TODO: Voor nu wordt MaybeBoolean.MAYBE en CANNOT_BE_AUTOMATED als simpelweg FALSE gezien
        true_voorstellen = [
            voorstel
            for voorstel in voorstellen
            if voorstel.mits.evaluation == MaybeBoolean.TRUE
        ]

        # TODO: het 1 voorstel geval qua output unifien met meerdere voorstellen
        # Er is 1 kloppende mits; Duidelijk
        if len(true_voorstellen) == 1:
            voorstel = true_voorstellen[0]
            return HabitatKeuze(
                status=KeuzeStatus.DUIDELIJK,
                opmerking=f"Er is een duidelijke keuze. Kloppende mits: {str(voorstel.mits)}",
                debug_info=f"{str(voorstel.vegtypeinfo)}",
                habitatvoorstellen=[voorstel],
            )

        # Er zijn meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
        if len(true_voorstellen) > 1:
            return HabitatKeuze(
                status=KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                opmerking=f"Er zijn meerdere habitatvoorstellen die aan hun mitsen voldoen; Kloppende mitsen: {[[str(voorstel.onderbouwend_vegtype), str(voorstel.mits)] for voorstel in true_voorstellen]}",
                debug_info=f"{[str(voorstel.vegtypeinfo) for voorstel in true_voorstellen]}",
                habitatvoorstellen=true_voorstellen,
            )

    # Er zijn geen kloppende mitsen gevonden; Alle voorstellen stellen dan dus H0000 voor
    # TODO: voorstellen niet veranderen, maar obv status H0000 printen in as_final in vegkartering
    for voorstel in habitatvoorstellen:
        voorstel.habtype = "H0000"
        voorstel.kwaliteit = None
    return HabitatKeuze(
        status=KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        opmerking=f"Er zijn geen habitatvoorstellen waarvan de mitsen kloppen. Mitsen waaraan niet is voldaan: {[[str(voorstel.onderbouwend_vegtype), str(voorstel.mits)] for voorstel in habitatvoorstellen]}",
        debug_info=f"{[str(voorstel.vegtypeinfo) for voorstel in habitatvoorstellen]}",
        habitatvoorstellen=habitatvoorstellen,
    )
