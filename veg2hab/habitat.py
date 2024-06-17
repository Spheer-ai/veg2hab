from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel

from veg2hab.criteria import BeperkendCriterium, GeenCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel, MaybeBoolean
from veg2hab.io.common import Interface
from veg2hab.mozaiek import GeenMozaiekregel, MozaiekRegel, is_mozaiek_type_present
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import VvN as _VvN


class HabitatVoorstel(BaseModel):
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    class config:
        extra = "forbid"

    onderbouwend_vegtype: Union[_SBB, _VvN, None]
    vegtype_in_dt: Union[_SBB, _VvN, None]
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

    @classmethod
    def HXXXX_niet_geautomatiseerd_SBB(cls, info: "VegTypeInfo"):
        assert len(info.SBB) > 0
        return cls(
            onderbouwend_vegtype=info.SBB[0],
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )


# TODO: dit zijn geen references meer nadat we ze opnieuw hebben ingeladen...
# Mogelijk willen de habitatvoorstellen hier dus uit halen..
class HabitatKeuze(BaseModel):
    class config:
        extra = "forbid"

    status: KeuzeStatus
    habtype: str  # format = "H1123"
    kwaliteit: Kwaliteit
    habitatvoorstellen: List[HabitatVoorstel]  # used as a refence
    opmerking: str = ""
    mits_opmerking: str = ""
    mozaiek_opmerking: str = ""
    debug_info: Optional[str] = ""

    def __post_init__(self):
        # Validatie
        if self.status in [
            KeuzeStatus.HABITATTYPE_TOEGEKEND,
        ]:
            assert self.habtype not in ["HXXXX", "H0000"]
        elif self.status in [
            KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
        ]:
            assert self.habtype == "H0000"
        elif self.status in [
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
            KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN,
        ]:
            assert self.habtype == "HXXXX"

        if self.habtype in ["H0000", "HXXXX"]:
            assert self.kwaliteit == Kwaliteit.NVT

    @classmethod
    def habitatkeuze_for_postponed_mozaiekregel(
        cls, habitatvoorstellen: List[HabitatVoorstel]
    ):
        return cls(
            status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            opmerking="",
            habitatvoorstellen=habitatvoorstellen,
            mits_opmerking="",
            mozaiek_opmerking="",
            debug_info="",
        )

    @property
    def zelfstandig(self):
        if self.habtype in ["H0000", "HXXXX"]:
            return True

        return is_mozaiek_type_present(self.habitatvoorstellen, GeenMozaiekregel)


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
                habitatvoorstellen=all_voorstellen,
                opmerking="",
                mits_opmerking="",
                mozaiek_opmerking="",
                debug_info="",
            )
        # ...of zijn er geen vegetatietypen opgegeven voor dit vlak
        assert all_voorstellen[0].onderbouwend_vegtype is None
        return HabitatKeuze(
            status=KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
            habtype="H0000",
            kwaliteit=all_voorstellen[0].kwaliteit,
            habitatvoorstellen=all_voorstellen,
            opmerking="",
            mits_opmerking="",
            mozaiek_opmerking="",
            debug_info="",
        )

    # Als er maar 1 habitatvoorstel is en dat is HXXXX, kan dat zijn omdat het vegetatietype niet geautomatiseerd is
    if len(all_voorstellen) == 1 and all_voorstellen[0].habtype == "HXXXX":
        voorstel = all_voorstellen[0]
        niet_geautomatiseerde_sbb = (
            Interface.get_instance().get_config().niet_geautomatiseerde_sbb
        )
        if str(voorstel.onderbouwend_vegtype) in niet_geautomatiseerde_sbb:
            assert isinstance(voorstel.onderbouwend_vegtype, _SBB)
            assert isinstance(voorstel.mits, GeenCriterium)
            assert isinstance(voorstel.mozaiek, GeenMozaiekregel)
            return HabitatKeuze(
                status=KeuzeStatus.NIET_GEAUTOMATISEERD_VEGTYPE,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=all_voorstellen,
                opmerking="",
                mits_opmerking="",
                mozaiek_opmerking="",
                debug_info="",
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
                    status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                    habtype=voorstel.habtype,
                    kwaliteit=voorstel.kwaliteit,
                    habitatvoorstellen=[voorstel],
                    opmerking="",
                    mits_opmerking=f"Mits: {voorstel.mits}, {voorstel.mits.evaluation}",
                    mozaiek_opmerking=f"Mozaiekregel: {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}",
                    debug_info="",
                )

            # ...of zijn er meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
            if len(true_voorstellen) > 1:
                return HabitatKeuze(
                    status=KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN,
                    habtype="HXXXX",
                    kwaliteit=Kwaliteit.NVT,
                    habitatvoorstellen=true_voorstellen,
                    opmerking="",
                    mits_opmerking="\n".join(
                        [
                            f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}]"
                            for voorstel in true_voorstellen
                        ]
                    ),
                    mozaiek_opmerking="\n".join(
                        [
                            f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}]"
                            for voorstel in true_voorstellen
                        ]
                    ),
                    debug_info="",
                )

            # ...of zijn er geen kloppende mitsen op het huidige match_level
            continue

        # Er is een niet-TRUE/FALSE truth value aanwezig. Dit kan of een CANNOT_BE_AUTOMATED zijn of een POSTPONE (of beide).
        # We gaan eerst kijken of er een CANNOT_BE_AUTOMATED is, want dan kan de keuze in latere iteraties nog steeds niet gemaakt worden

        # Als er een CANNOT_BE_AUTOMATED is...
        if MaybeBoolean.CANNOT_BE_AUTOMATED in truth_values:
            # ...dan kunnen we voor de huidige voorstellen geen keuze maken

            # We weten wel dat habitatvoorstellen met een specifieker matchniveau dan die van
            # de current_voorstellen allemaal FALSE waren, dus die hoeven we niet terug te geven
            # We filteren ook mits&mozaiek eruit die FALSE zijn; die hangen nm toch niet van een NietGeautomatiseerdCriterium af.
            return_voorstellen = [
                voorstel
                for voorstel in all_voorstellen
                if voorstel.match_level <= current_voorstellen[0].match_level
                and (
                    voorstel.mits.evaluation & voorstel.mozaiek.evaluation
                    != MaybeBoolean.FALSE
                )
            ]

            return HabitatKeuze(
                status=KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=return_voorstellen,
                opmerking="",
                mits_opmerking="\n".join(
                    [
                        f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}]"
                        for voorstel in return_voorstellen
                    ]
                ),
                mozaiek_opmerking="\n".join(
                    [
                        f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}]"
                        for voorstel in return_voorstellen
                    ]
                ),
                debug_info="",
            )

        # Als er een POSTPONE is...
        if MaybeBoolean.POSTPONE in truth_values:
            # ...dan komt dat door een mozaiekregel waar nog te weinig info over omliggende vlakken voor is

            # We weten wel dat habitatvoorstellen met een specifieker matchniveau dan die van
            # de current_voorstellen allemaal FALSE waren, dus die hoeven we niet terug te geven
            # We filteren ook mits&mozaiek eruit die FALSE zijn; die hangen nm toch niet van een NietGeautomatiseerdCriterium af.
            return_voorstellen = [
                voorstel
                for voorstel in all_voorstellen
                if voorstel.match_level <= current_voorstellen[0].match_level
                and (
                    voorstel.mits.evaluation & voorstel.mozaiek.evaluation
                    != MaybeBoolean.FALSE
                )
            ]

            # Deze keuze komt volgende iteratieronde terug
            # Als de huidige iteratie de laatste is (bv omdat er geen voortang is gemaakt), dan komt deze keuze in de output terecht.
            return HabitatKeuze(
                status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=return_voorstellen,
                opmerking="",
                mits_opmerking="\n".join(
                    [
                        f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}]"
                        for voorstel in return_voorstellen
                    ]
                ),
                mozaiek_opmerking="\n".join(
                    [
                        f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}]"
                        for voorstel in return_voorstellen
                    ]
                ),
                debug_info="",
            )

    # Er zijn geen kloppende mitsen gevonden;
    return HabitatKeuze(
        status=KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
        habtype="H0000",
        kwaliteit=Kwaliteit.NVT,
        habitatvoorstellen=all_voorstellen,
        opmerking="",
        mits_opmerking="\n".join(
            [
                f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}]"
                for voorstel in all_voorstellen
            ]
        ),
        mozaiek_opmerking="\n".join(
            [
                f"[{voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}]"
                for voorstel in all_voorstellen
            ]
        ),
        debug_info="",
    )


def calc_nr_of_unresolved_habitatkeuzes_per_row(gdf):
    """
    Telt het aantal nog niet gemaakte habitatkeuzes. Dit zijn None habkeuzes en
    uitgestelde mozaiek-habitatkeuzes (die met status=KeuzeStatus.WACHTEN_OP_MOZAIEK per rij)
    """
    assert "HabitatKeuze" in gdf.columns, "HabitatKeuze kolom niet aanwezig in gdf"

    return gdf.HabitatKeuze.apply(
        lambda keuzes: sum(
            [
                (keuze is None or keuze.status == KeuzeStatus.WACHTEN_OP_MOZAIEK)
                for keuze in keuzes
            ]
        )
    )
