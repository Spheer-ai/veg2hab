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
from veg2hab.enums import KeuzeStatus, Kwaliteit, MaybeBoolean
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import MatchLevel
from veg2hab.vegetatietypen import VvN as _VvN


@dataclass
class HabitatVoorstel:
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    onderbouwend_vegtype: Optional[Union[_SBB, _VvN]]
    vegtype_in_dt: Optional[Union[_SBB, _VvN]]
    habtype: str
    kwaliteit: Kwaliteit
    idx_in_dt: Optional[int]
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
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )

    @classmethod
    def H0000_no_vegtype_present(cls):
        return cls(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )


@dataclass
class HabitatKeuze:
    status: KeuzeStatus
    habtype: str  # format = "H1123"
    kwaliteit: Kwaliteit
    opmerking: str
    debug_info: Optional[str]
    habitatvoorstellen: List[HabitatVoorstel]  # used as a refence

    def __post_init__(self):
        if self.status in [
            KeuzeStatus.DUIDELIJK,
        ]:
            assert self.habtype not in ["HXXXX", "H0000"]
        elif self.status in [
            KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
        ]:
            assert self.habtype == "H0000"
        elif self.status in [
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.PLACEHOLDER_CRITERIA,
            KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
        ]:
            assert self.habtype == "HXXXX"


def is_criteria_type_present(
    voorstellen: Union[List[List[HabitatVoorstel]], List[HabitatVoorstel]],
    criteria_type: BeperkendCriterium,
) -> bool:
    """
    Geeft True als er in de lijst met voorstellen eentje met een criteria van crit_type is
    Nodig om te bepalen waarmee de gdf verrijkt moet worden (FGR etc)
    """
    # Als we een lijst van lijsten hebben, dan flattenen we die
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
    voorstellen: Union[List[List[HabitatVoorstel]], List[HabitatVoorstel]],
    mozaiek_type: Mozaiekregel,
) -> bool:
    """
    Geeft True als er in de lijst met habitatvoorstellen eentje met een mozaiekregel van mozaiek_type is
    NOTE: Op het moment wordt dit gebruikt om te kijken of er dummymozaiekregels zijn, en zo ja, dan wordt er HXXXX gegeven.
    NOTE: Zodra mozaiekregels geimplementeerd zijn, kan deze functie mogelijk weg
    """
    # Als we een lijst van lijsten hebben, dan flattenen we die
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
    Tuple waar op gesort wordt: [uiteindelijk habtype=="H0000", 100-percentage, kwaliteit==Kwaliteit.MATIG]
    """
    keuze, vegtypeinfo = keuze_en_vegtypeinfo

    habtype_is_H0000 = keuze.habtype == "H0000"
    percentage = vegtypeinfo.percentage
    kwaliteit_is_matig = keuze.kwaliteit == [Kwaliteit.MATIG]

    return (habtype_is_H0000, 100 - percentage, kwaliteit_is_matig)


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


def habitatkeuze_obv_mitsen(all_voorstellen: List[HabitatVoorstel]) -> HabitatKeuze:
    """
    Creeert een habitatkeuze obv de mitsen van habitatvoorstellen
    Als er mozaikegels zijn, dan wordt er een HabitatKeuze met status WACHTEN_OP_MOZAIEK gegeven
    """
    assert len(all_voorstellen) > 0, "Er zijn geen habitatvoorstellen"

    # Als er maar 1 habitatvoorstel is en dat is H0000, dan...
    if len(all_voorstellen) == 1 and all_voorstellen[0].habtype == "H0000":
        # ...zat of geen van de vegtypen in de deftabel
        if all_voorstellen[0].onderbouwend_vegtype:
            return HabitatKeuze(
                status=KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
                habtype="H0000",
                kwaliteit=all_voorstellen[0].kwaliteit,
                opmerking="",
                debug_info="",
                habitatvoorstellen=all_voorstellen,
            )
        # ...of zijn er geen vegetatietypen opgegeven voor dit vlak
        assert all_voorstellen[0].onderbouwend_vegtype is None
        return HabitatKeuze(
            status=KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
            habtype="H0000",
            kwaliteit=all_voorstellen[0].kwaliteit,
            opmerking="",
            debug_info="",
            habitatvoorstellen=all_voorstellen,
        )

    # NOTE: Tijdelijke dummy check voor mozaiek
    if is_mozaiek_type_present(all_voorstellen, DummyMozaiekregel):
        return HabitatKeuze(
            status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.ONBEKEND,
            opmerking=f"Er zijn habitatvoorstellen met mozaiekregels: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mozaiek)] for voorstel in all_voorstellen]}",
            debug_info="",
            habitatvoorstellen=all_voorstellen,
        )

    sublisted_voorstellen = sublist_per_match_level(all_voorstellen)

    # Per MatchLevel checken of er kloppende mitsen zijn
    for current_voorstellen in sublisted_voorstellen:
        
        truth_values = [voorstel.mits.evaluation for voorstel in current_voorstellen]

        # Als er enkel TRUE en FALSE zijn, dan...
        if all([value in [MaybeBoolean.TRUE, MaybeBoolean.FALSE] for value in truth_values]):
            true_voorstellen = [
                voorstel
                for voorstel in current_voorstellen
                if voorstel.mits.evaluation == MaybeBoolean.TRUE
            ]

            # ...is er 1 kloppende mits; Duidelijk
            if len(true_voorstellen) == 1:
                voorstel = true_voorstellen[0]
                return HabitatKeuze(
                    status=KeuzeStatus.DUIDELIJK,
                    habtype=voorstel.habtype,
                    kwaliteit=voorstel.kwaliteit,
                    opmerking=f"Er is een duidelijke keuze. Kloppende mits: {str(voorstel.mits)}",
                    debug_info="",
                    habitatvoorstellen=[voorstel],
                )

            # ...of zijn er meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
            if len(true_voorstellen) > 1:
                return HabitatKeuze(
                    status=KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                    habtype="HXXXX",
                    kwaliteit=Kwaliteit.ONBEKEND,
                    opmerking=f"Er zijn meerdere habitatvoorstellen die aan hun mitsen voldoen; Kloppende mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in true_voorstellen]}",
                    debug_info="",
                    habitatvoorstellen=true_voorstellen,
                )
            
            # ...of zijn er geen kloppende mitsen op het huidige match_level
            continue
            
        # Er is een niet-TRUE/FALSE waarde aanwezig. Op het moment van schrijven kan dit enkel
        # MaybeBoolean.CANNOT_BE_AUTOMATED zijn, wat altijd het gevolg is van een PlaceholderCriterium.
        # Als we later meer MaybeBoolean waarden toevoegen klapt hij er hier uit zodat ik niet vergeet om dit te updaten
        assert MaybeBoolean.CANNOT_BE_AUTOMATED in truth_values, "Er is een onbekende (niet TRUE, FALSE of CANNOT_BE_AUTOMATED) waarde in de mitsen"
        assert is_criteria_type_present([current_voorstellen], PlaceholderCriterium), "Er is een CANNOT_BE_AUTOMATED waarde in de mitsen, maar er is geen PlaceholderCriterium"

        # Op het huidige matchlevel zijn er mitsen die niet geautomatiseerd kunnen worden.
        # We kunnen dus niet bepalen welke van de huidige en nog te behandelen 
        # voorstellen moet leiden tot een Habitattype.
            
        # We weten wel dat habitatvoorstellen met een specifieker matchniveau dan die van 
        # de current_voorstellen allemaal FALSE waren, dus die hoeven we niet terug te geven
        return_voorstellen = [
            voorstel
            for voorstel in all_voorstellen
            if voorstel.match_level <= current_voorstellen[0].match_level
        ]
        
        return HabitatKeuze(
            status=KeuzeStatus.PLACEHOLDER_CRITERIA,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.ONBEKEND,
            opmerking=f"Er zijn mitsen met nog niet geimplementeerde criteria. Alle mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in all_voorstellen]}",
            debug_info="",
            habitatvoorstellen=return_voorstellen,
        )
    
    # Er zijn geen kloppende mitsen gevonden;
    return HabitatKeuze(
        status=KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        habtype="H0000",
        kwaliteit=Kwaliteit.NVT,
        opmerking=f"Er zijn geen habitatvoorstellen waarvan de mitsen kloppen. Mitsen waaraan niet is voldaan: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in all_voorstellen]}",
        debug_info="",
        habitatvoorstellen=all_voorstellen,
    )
            

# TODO: een habitatkeuze obv mitsen en mozaiek functie
