import json
from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, root_validator, validator

from veg2hab.criteria import BeperkendCriterium, GeenCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel, MaybeBoolean
from veg2hab.io.common import Interface
from veg2hab.mozaiek import GeenMozaiekregel, MozaiekRegel, is_mozaiek_type_present
from veg2hab.vegetatietypen import SBB, VvN


class HabitatVoorstel(BaseModel):
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    class Config:
        extra = "forbid"
        validate_assignment = True

    onderbouwend_vegtype: Union[SBB, VvN, None]
    vegtype_in_dt: Union[SBB, VvN, None]
    habtype: str
    kwaliteit: Kwaliteit
    mits: BeperkendCriterium
    mozaiek: MozaiekRegel
    match_level: MatchLevel
    vegtype_in_dt_naam: str = ""
    habtype_naam: str = ""

    @classmethod
    def H0000_vegtype_not_in_dt(cls, info: "VegTypeInfo"):
        return cls(
            onderbouwend_vegtype=info.VvN[0]
            if info.VvN
            else (info.SBB[0] if info.SBB else None),
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
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
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )

    def _get_dftbl_str(self):
        veg_str = str(self.vegtype_in_dt)
        if self.vegtype_in_dt_naam != "":
            veg_str += f" ({self.vegtype_in_dt_naam})"

        hab_str = self.habtype
        if self.habtype_naam != "":
            hab_str += f" ({self.habtype_naam})"

        return f"{veg_str} -> {hab_str}"

    def get_VvNdftbl_str(self):
        if isinstance(self.vegtype_in_dt, SBB):
            return "---"

        return self._get_dftbl_str()

    def get_SBBdftbl_str(self):
        if isinstance(self.vegtype_in_dt, VvN):
            return "---"

        return self._get_dftbl_str()

    @staticmethod
    def serialize_list2(voorstellen: List[List["HabitatVoorstel"]]) -> str:
        return json.dumps(
            [[json.loads(v.json()) for v in sublist] for sublist in voorstellen]
        )

    @staticmethod
    def deserialize_list2(serialized: str) -> List[List["HabitatVoorstel"]]:
        return [
            [HabitatVoorstel(**v) for v in sublist]
            for sublist in json.loads(serialized)
        ]


class HabitatKeuze(BaseModel):
    class config:
        extra = "forbid"
        validate_assignment = True

    status: KeuzeStatus
    habtype: str  # format = "H1123"
    kwaliteit: Kwaliteit
    habitatvoorstellen: List[HabitatVoorstel]  # used as a refence
    info: str = ""
    mits_info: str = ""
    mozaiek_info: str = ""

    @root_validator
    def valideer_habtype_keuzestatus(cls, values):
        status = values.get("status")
        habtype = values.get("habtype")
        kwaliteit = values.get("kwaliteit")

        if status in [
            KeuzeStatus.HABITATTYPE_TOEGEKEND,
        ]:
            assert habtype not in ["HXXXX", "H0000"]
        elif status in [
            KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
        ]:
            assert habtype == "H0000"
        elif status in [
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
            KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN,
        ]:
            assert habtype == "HXXXX"
        if habtype in ["H0000", "HXXXX"]:
            assert kwaliteit == Kwaliteit.NVT

        return values

    @validator(
        "info",
        "mits_info",
        "mozaiek_info",
        pre=True,
        always=True,
    )
    def vervang_none_door_lege_string(cls, v):
        """
        Omdat ArcGIS niet om kan gaan met lege strings worden deze fields weggeschreven als None
        Bij het deserializen worden deze dus ook ingelezen als None
        Dus we zetten ze hier weer om naar een lege string :)
        """
        return v if pd.notna(v) else ""

    def __init__(self, **data):
        super().__init__(**data)
        self.update_info()

    @classmethod
    def habitatkeuze_for_postponed_mozaiekregel(
        cls, habitatvoorstellen: List[HabitatVoorstel]
    ):
        return cls(
            status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            info="",
            habitatvoorstellen=habitatvoorstellen,
            mits_info="",
            mozaiek_info="",
        )

    @property
    def zelfstandig(self):
        if self.habtype in ["H0000", "HXXXX"]:
            return True

        return is_mozaiek_type_present(self.habitatvoorstellen, GeenMozaiekregel)

    @staticmethod
    def serialize_list(keuzes: List["HabitatKeuze"]) -> str:
        return json.dumps([json.loads(v.json()) for v in keuzes])

    @staticmethod
    def deserialize_list(serialized: str) -> List["HabitatKeuze"]:
        return [HabitatKeuze(**v) for v in json.loads(serialized)]

    def update_info(self):
        """
        Verzamelt de infos van alle habitatvoorstellen en voegt deze toe aan de info van de habitatkeuze
        """
        assert len(self.habitatvoorstellen) > 0, "Er zijn geen habitatvoorstellen"

        if pd.isnull(self.info):
            self.info = ""

        all_infos = set.union(
            *[voorstel.mits.get_info() for voorstel in self.habitatvoorstellen]
        )

        # Dubbelingen voorkomen
        filtered_infos = [info for info in all_infos if info not in self.info]
        filtered_infos.append(self.info)

        self.info = ("\n".join(filtered_infos)).strip()


def rank_habitatkeuzes(
    keuze_vegtypeinfo_en_voorstellen: Tuple[
        HabitatKeuze, "VegTypeInfo", List[HabitatVoorstel]
    ]
) -> tuple:
    """
    Returned een tuple voor het sorteren van een lijst habitatkeuzes + vegtypeinfos + habitatvoorstellen
    We zetten eerst alle H0000 achteraan, daarna sorteren we op percentage, daarna op kwaliteit
    Tuple waar op gesort wordt: [keuze.habtype == "H0000", 100 - percentage, keuze.kwaliteit == Kwaliteit.MATIG]
    """
    # Voorstellen laten we in _ want die zijn niet nodig voor het bepalen van de volgorde
    keuze, vegtypeinfo, _ = keuze_vegtypeinfo_en_voorstellen

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
            return HabitatKeuze(
                status=KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
                habtype="H0000",
                kwaliteit=all_voorstellen[0].kwaliteit,
                habitatvoorstellen=all_voorstellen,
                info="",
                mits_info="",
                mozaiek_info="",
            )
        # ...of zijn er geen vegetatietypen opgegeven voor dit vlak
        assert all_voorstellen[0].onderbouwend_vegtype is None
        return HabitatKeuze(
            status=KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
            habtype="H0000",
            kwaliteit=all_voorstellen[0].kwaliteit,
            habitatvoorstellen=all_voorstellen,
            info="",
            mits_info="",
            mozaiek_info="",
        )

    # Als er maar 1 habitatvoorstel is en dat is HXXXX, kan dat zijn omdat het vegetatietype niet geautomatiseerd is
    if len(all_voorstellen) == 1 and all_voorstellen[0].habtype == "HXXXX":
        voorstel = all_voorstellen[0]
        niet_geautomatiseerde_sbb = (
            Interface.get_instance().get_config().niet_geautomatiseerde_sbb
        )
        if str(voorstel.onderbouwend_vegtype) in niet_geautomatiseerde_sbb:
            assert isinstance(voorstel.onderbouwend_vegtype, SBB)
            assert isinstance(voorstel.mits, GeenCriterium)
            assert isinstance(voorstel.mozaiek, GeenMozaiekregel)
            return HabitatKeuze(
                status=KeuzeStatus.NIET_GEAUTOMATISEERD_VEGTYPE,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=all_voorstellen,
                info="",
                mits_info="",
                mozaiek_info="",
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
                    info="",
                    mits_info="\n".join(
                        [
                            f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                            for nr, voorstel in enumerate(all_voorstellen)
                        ]
                    ),
                    mozaiek_info="\n".join(
                        [
                            f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                            for nr, voorstel in enumerate(all_voorstellen)
                        ]
                    ),
                )

            # ...of zijn er meerdere kloppende mitsen; Alle info van de kloppende mitsen meegeven
            if len(true_voorstellen) > 1:
                if all(
                    [
                        voorstel.habtype == true_voorstellen[0].habtype
                        for voorstel in true_voorstellen
                    ]
                ) and all(
                    [
                        voorstel.kwaliteit == true_voorstellen[0].kwaliteit
                        for voorstel in true_voorstellen
                    ]
                ):
                    return HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype=true_voorstellen[0].habtype,
                        kwaliteit=true_voorstellen[0].kwaliteit,
                        habitatvoorstellen=all_voorstellen,
                        info=f"",
                        mits_info="\n".join(
                            [
                                f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                                for nr, voorstel in enumerate(all_voorstellen)
                            ]
                        ),
                        mozaiek_info="\n".join(
                            [
                                f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                                for nr, voorstel in enumerate(all_voorstellen)
                            ]
                        ),
                    )
                return HabitatKeuze(
                    status=KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN,
                    habtype="HXXXX",
                    kwaliteit=Kwaliteit.NVT,
                    habitatvoorstellen=all_voorstellen,
                    info="",
                    mits_info="\n".join(
                        [
                            f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                            for nr, voorstel in enumerate(all_voorstellen)
                        ]
                    ),
                    mozaiek_info="\n".join(
                        [
                            f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                            for nr, voorstel in enumerate(all_voorstellen)
                        ]
                    ),
                )

            # ...of zijn er geen kloppende mitsen op het huidige match_level
            continue

        # Er is een niet-TRUE/FALSE truth value aanwezig. Dit kan of een CANNOT_BE_AUTOMATED zijn of een POSTPONE (of beide).
        # We gaan eerst kijken of er een CANNOT_BE_AUTOMATED is, want dan kan de keuze in latere iteraties nog steeds niet gemaakt worden

        # Als er een CANNOT_BE_AUTOMATED is...
        if MaybeBoolean.CANNOT_BE_AUTOMATED in truth_values:
            # ...dan kunnen we voor de huidige voorstellen geen keuze maken
            return HabitatKeuze(
                status=KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=all_voorstellen,
                info="",
                mits_info="\n".join(
                    [
                        f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                        for nr, voorstel in enumerate(all_voorstellen)
                    ]
                ),
                mozaiek_info="\n".join(
                    [
                        f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                        for nr, voorstel in enumerate(all_voorstellen)
                    ]
                ),
            )

        # Als er een POSTPONE is...
        if MaybeBoolean.POSTPONE in truth_values:
            # ...dan komt dat door een mozaiekregel waar nog te weinig info over omliggende vlakken voor is

            # Deze keuze komt volgende iteratieronde terug
            # Als de huidige iteratie de laatste is (bv omdat er geen voortgang is gemaakt), dan komt deze keuze in de output terecht.
            return HabitatKeuze(
                status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
                habtype="HXXXX",
                kwaliteit=Kwaliteit.NVT,
                habitatvoorstellen=all_voorstellen,
                info="",
                mits_info="\n".join(
                    [
                        f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                        for nr, voorstel in enumerate(all_voorstellen)
                    ]
                ),
                mozaiek_info="\n".join(
                    [
                        f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                        for nr, voorstel in enumerate(all_voorstellen)
                    ]
                ),
            )

    # Er zijn geen kloppende mitsen gevonden;
    return HabitatKeuze(
        status=KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
        habtype="H0000",
        kwaliteit=Kwaliteit.NVT,
        habitatvoorstellen=all_voorstellen,
        info="",
        mits_info="\n".join(
            [
                f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mits}, {voorstel.mits.evaluation}"
                for nr, voorstel in enumerate(all_voorstellen)
            ]
        ),
        mozaiek_info="\n".join(
            [
                f"{nr + 1}. {voorstel.vegtype_in_dt}, {voorstel.habtype}, {voorstel.mozaiek}, {voorstel.mozaiek.evaluation}"
                for nr, voorstel in enumerate(all_voorstellen)
            ]
        ),
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
