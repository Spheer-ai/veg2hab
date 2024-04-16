from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from veg2hab.criteria import BeperkendCriterium, GeenCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel, MaybeBoolean
from veg2hab.mozaiek import GeenMozaiekregel, MozaiekRegel
from veg2hab.vegetatietypen import SBB as _SBB
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
    mozaiek: MozaiekRegel
    match_level: MatchLevel
    mozaiek_dict: Optional[dict] = None

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
    zelfstandig: bool
    opmerking: str
    mits_opmerking: str
    mozaiek_opmerking: str
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
            KeuzeStatus.PLACEHOLDER,
            KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
        ]:
            assert self.habtype == "HXXXX"


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


def _sublist_per_match_level(
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


def try_to_determine_habkeuze(
    all_voorstellen: List[HabitatVoorstel],
) -> Union[HabitatKeuze, None]:
    """
    Probeert op basis van de voorstellen een HabitatKeuze te maken. Als er een keuze gemaakt kan worden
    wordt (
    """

    assert len(all_voorstellen) > 0, "Er zijn geen habitatvoorstellen"

    # Als er maar 1 habitatvoorstel is en dat is H0000, dan...
    if len(all_voorstellen) == 1 and all_voorstellen[0].habtype == "H0000":
        # ...zat of geen van de vegtypen in de deftabel
        if all_voorstellen[0].onderbouwend_vegtype:
            assert all_voorstellen[0].idx_in_dt is None
            return HabitatKeuze(
                status=KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
                habtype="H0000",
                kwaliteit=all_voorstellen[0].kwaliteit,
                zelfstandig=True,
                opmerking="Geen van de opgegeven vegetatietypen is teruggevonden in de definitietabel.",
                mits_opmerking="",
                mozaiek_opmerking="",
                debug_info="",
                habitatvoorstellen=all_voorstellen,
            )
        # ...of zijn er geen vegetatietypen opgegeven voor dit vlak
        assert all_voorstellen[0].onderbouwend_vegtype is None
        return HabitatKeuze(
            status=KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
            habtype="H0000",
            kwaliteit=all_voorstellen[0].kwaliteit,
            zelfstandig=True,
            opmerking="Er zijn geen vegetatietypen opgegeven voor dit vlak.",
            mits_opmerking="",
            mozaiek_opmerking="",
            debug_info="",
            habitatvoorstellen=all_voorstellen,
        )

    sublisted_voorstellen = _sublist_per_match_level(all_voorstellen)

    # Per MatchLevel checken of er kloppende mitsen zijn
    for current_voorstellen in sublisted_voorstellen:
        truth_values_mits = [
            voorstel.mits.evaluation for voorstel in current_voorstellen
        ]
        truth_values_mozaiek = [
            voorstel.mozaiek.evaluation for voorstel in current_voorstellen
        ]
        combined = zip(truth_values_mits, truth_values_mozaiek)
        truth_values = [mits & mozaiek for mits, mozaiek in combined]

        # Als er enkel TRUE en FALSE zijn, dan...
        if all(
            [value in [MaybeBoolean.TRUE, MaybeBoolean.FALSE] for value in truth_values]
        ):
            true_voorstellen = [
                voorstel
                for voorstel, truth_value in zip(current_voorstellen, truth_values)
                if truth_value == MaybeBoolean.TRUE
            ]

            # ...is er 1 kloppende mits; Duidelijk
            if len(true_voorstellen) == 1:
                voorstel = true_voorstellen[0]
                return HabitatKeuze(
                    status=KeuzeStatus.DUIDELIJK,
                    habtype=voorstel.habtype,
                    kwaliteit=voorstel.kwaliteit,
                    zelfstandig=True,
                    opmerking=f"Er is een duidelijke keuze. Kloppende mits en kloppende mozaiek.",
                    mits_opmerking=str(voorstel.mits),
                    mozaiek_opmerking=str(voorstel.mozaiek),
                    debug_info="",
                    habitatvoorstellen=[voorstel],
                )

            # ...of zijn er meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
            if len(true_voorstellen) > 1:
                return HabitatKeuze(
                    status=KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                    habtype="HXXXX",
                    kwaliteit=Kwaliteit.ONBEKEND,
                    zelfstandig=True,
                    opmerking=f"Er zijn meerdere habitatvoorstellen die aan hun mitsen/mozaieken voldoen; zie mits/mozk_opm voor meer info in format [opgegevenvegtype, potentieel habtype, mits/mozaiek]",
                    mits_opmerking=f"Kloppende mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in true_voorstellen]}",
                    mozaiek_opmerking=f"Kloppende mozaiekregels: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mozaiek)] for voorstel in true_voorstellen]}",
                    debug_info="",
                    habitatvoorstellen=true_voorstellen,
                )

            # ...of zijn er geen kloppende mitsen op het huidige match_level
            continue

        # Er is een niet-TRUE/FALSE truth value aanwezig. Dit kan of een CANNOT_BE_AUTOMATED zijn of een POSTPONE (of beide).

        # Als er een CANNOT_BE_AUTOMATED is...
        if MaybeBoolean.CANNOT_BE_AUTOMATED in truth_values:
            # ...dan kunnen we voor de huidige voorstellen geen keuze maken

            # We weten wel dat habitatvoorstellen met een specifieker matchniveau dan die van
            # de current_voorstellen allemaal FALSE waren, dus die hoeven we niet terug te geven
            return_voorstellen = [
                voorstel
                for voorstel in all_voorstellen
                if voorstel.match_level <= current_voorstellen[0].match_level
            ]

            return HabitatKeuze(
                status=KeuzeStatus.PLACEHOLDER,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.ONBEKEND,
                zelfstandig=True,
                opmerking=f"Er zijn mitsen of mozaiekregels die nog niet geimplementeerde zijn. Zie mits/mozk_opm voor meer info in format [opgegevenvegtype, potentieel habtype, mits/mozaiek]",
                mits_opmerking=f"Alle mitsen: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in all_voorstellen]}",
                mozaiek_opmerking=f"Alle mozaiekregels: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mozaiek)] for voorstel in all_voorstellen]}",
                debug_info="",
                habitatvoorstellen=return_voorstellen,
            )

        # Als er een POSTPONE is...
        if MaybeBoolean.POSTPONE in truth_values:
            # ...dan komt dat door een mozaiekregel waar nog te weinig info over omliggende vlakken voor is
            # We returnen dan None, zodat we later nog een keer kunnen proberen.
            return None

    # Er zijn geen kloppende mitsen gevonden;
    return HabitatKeuze(
        status=KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        habtype="H0000",
        kwaliteit=Kwaliteit.NVT,
        zelfstandig=True,
        opmerking=f"Er zijn geen habitatvoorstellen waarvan en de mitsen en de mozaiekregels kloppen. Zie mits/mozk_opm voor meer info in format [opgegevenvegtype, potentieel habtype, mits/mozaiek].",
        mits_opmerking=f"Mitsen waaraan mogelijk niet is voldaan: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mits)] for voorstel in all_voorstellen]}",
        mozaiek_opmerking=f"Mozaiekregels waaraan mogelijk niet is voldaan: {[[str(voorstel.onderbouwend_vegtype), voorstel.habtype, str(voorstel.mozaiek)] for voorstel in all_voorstellen]}",
        debug_info="",
        habitatvoorstellen=all_voorstellen,
    )
