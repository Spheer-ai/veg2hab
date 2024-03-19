import enum
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from veg2hab.criteria import (
    BeperkendCriterium,
    DummyMozaiekregel,
    GeenCriterium,
    GeenMozaiekregel,
    Mozaiekregel,
    PlaceholderCriterium,
)
from veg2hab.enums import Kwaliteit, MaybeBoolean
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
    habtype: str
    kwaliteit: Kwaliteit
    idx_in_dt: int
    mits: BeperkendCriterium
    mozaiek: Mozaiekregel
    match_level: MatchLevel

    @classmethod
    def H0000_vegtype_not_in_dt(cls, info: "VegTypeInfo"):
        return cls(
            onderbouwend_vegtype=info.VvN[0]
            if info.VvN
            else (info.SBB[0] if info.SBB else None),
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=None,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
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

    # Er zijn PlaceholderCriteriums, dus handmatige controle
    PLACEHOLDER_CRITERIA = enum.auto()

    HANDMATIGE_CONTROLE = enum.auto()
    WACHTEN_OP_MOZAIEK = enum.auto()


@dataclass
class HabitatKeuze:
    status: str
    opmerking: str
    debug_info: Optional[str]
    habitatvoorstellen: List[HabitatVoorstel]
    # TODO willen we dit nog opschonen?! Baseclass maken zonder mitsen?


def is_criteria_type_present(
    voorstellen: Union[List[List[HabitatVoorstel]], List[HabitatVoorstel]],
    criteria_type,
):
    """
    Geeft True als er in de lijst met Criteria eentje van crit_type is
    Nodig om te bepalen waarmee de gdf verrijkt moet worden (FGR etc)
    """
    # if we are dealing with a list of lists, we flatten it
    if any(isinstance(i, list) for i in voorstellen):
        voorstellen = [item for sublist in voorstellen for item in sublist]
    return any(
        (
            voorstel.mits.is_criteria_type_present(criteria_type)
            if voorstel.mits is not None
            else False
        )
        for voorstel in voorstellen
    )


def is_mozaiek_type_present(
    voorstellen: Union[List[List[HabitatVoorstel]], List[HabitatVoorstel]], mozaiek_type
):
    """
    Geeft True als er in de lijst met Criteria eentje van crit_type is
    Nodig om te bepalen waarmee de gdf verrijkt moet worden (FGR etc)
    """
    # if we are dealing with a list of lists, we flatten it
    if any(isinstance(i, list) for i in voorstellen):
        voorstellen = [item for sublist in voorstellen for item in sublist]
    return any(
        (
            voorstel.mozaiek.is_mozaiek_type_present(mozaiek_type)
            if voorstel.mozaiek is not None
            else False
        )
        for voorstel in voorstellen
    )


def rank_habitatkeuzes(
    keuze_en_vegtypeinfo: Tuple[HabitatKeuze, "VegTypeInfo"]
) -> tuple:
    """
    Returned een tuple voor het sorteren van een lijst habitatkeuzes + vegtypeinfos voor in de outputtabel
    We zetten eerst alle H0000 achteraan, daarna sorteren we op percentage, daarna op kwaliteit
    """
    keuze, vegtypeinfo = keuze_en_vegtypeinfo
    voorgestelde_habtypen = [voorstel.habtype for voorstel in keuze.habitatvoorstellen]
    alleen_H0000 = all(habtype == "H0000" for habtype in voorgestelde_habtypen)

    percentage = vegtypeinfo.percentage

    voorgestelde_kwaliteiten = [
        voorstel.kwaliteit for voorstel in keuze.habitatvoorstellen
    ]
    matig_kwaliteit = voorgestelde_kwaliteiten == [Kwaliteit.MATIG]

    return (alleen_H0000, 100 - percentage, matig_kwaliteit)


def sublist_per_match_level(
    voorstellen: List[HabitatVoorstel],
) -> List[List[HabitatVoorstel]]:
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
            debug_info="",
            habitatvoorstellen=habitatvoorstellen,
        )

    # NOTE: Tijdelijke dummy check voor mozaiek
    if is_mozaiek_type_present(habitatvoorstellen, DummyMozaiekregel):
        return HabitatKeuze(
            status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
            opmerking=f"Er zijn habitatvoorstellen met mozaiekregels: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mozaiek)] for voorstel in habitatvoorstellen]}",
            debug_info="",
            habitatvoorstellen=habitatvoorstellen,
        )

    # Als er een PlaceholderCriterium dan moet er handmatig gecontroleerd worden
    if is_criteria_type_present([habitatvoorstellen], PlaceholderCriterium):
        return HabitatKeuze(
            status=KeuzeStatus.PLACEHOLDER_CRITERIA,
            opmerking=f"Er zijn mitsen met nog niet geimplementeerde criteria. Alle mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in habitatvoorstellen]}",
            debug_info="",
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
                debug_info="",
                habitatvoorstellen=[voorstel],
            )

        # Er zijn meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
        if len(true_voorstellen) > 1:
            return HabitatKeuze(
                status=KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                opmerking=f"Er zijn meerdere habitatvoorstellen die aan hun mitsen voldoen; Kloppende mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in true_voorstellen]}",
                debug_info="",
                habitatvoorstellen=true_voorstellen,
            )

    # Er zijn geen kloppende mitsen gevonden;
    return HabitatKeuze(
        status=KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        opmerking=f"Er zijn geen habitatvoorstellen waarvan de mitsen kloppen. Mitsen waaraan niet is voldaan: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in habitatvoorstellen]}",
        debug_info="",
        habitatvoorstellen=habitatvoorstellen,
    )


# TODO: een habitatkeuze obv mitsen en mozaiek functie
