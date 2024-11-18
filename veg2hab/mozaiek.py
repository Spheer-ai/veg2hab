import logging
from collections import defaultdict, namedtuple
from numbers import Number
from typing import ClassVar, Dict, List, NamedTuple, Optional, Set, Tuple, Union

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel, Field, PrivateAttr

from veg2hab.enums import Kwaliteit, MaybeBoolean, NumberType
from veg2hab.io.common import Interface
from veg2hab.vegetatietypen import SBB, VvN


class MozkPercTuple(NamedTuple):
    habtype: str
    kwaliteit: Kwaliteit
    percentage: NumberType


class MozaiekRegel(BaseModel):
    type: ClassVar[Optional[str]] = None
    _subtypes_: ClassVar[dict] = dict()
    mozaiek_threshold: NumberType = Field(
        default_factory=lambda: Interface.get_instance().get_config().mozaiek_threshold
    )
    mozaiek_als_rand_threshold: NumberType = Field(
        default_factory=lambda: Interface.get_instance()
        .get_config()
        .mozaiek_als_rand_threshold
    )
    mozaiek_minimum_bedekking: NumberType = Field(
        default_factory=lambda: Interface.get_instance()
        .get_config()
        .mozaiek_minimum_bedekking
    )

    def __init_subclass__(cls):
        # Vul de _subtypes_ dict met alle subclasses
        if cls.type is None:
            raise ValueError(
                "You should specify the `type: ClassVar[str] = 'EnCritera'`"
            )
        cls._subtypes_[cls.type] = cls

    def __new__(cls, *args, **kwargs):
        # Maakt de juiste subclass aan op basis van de type parameter
        if cls == MozaiekRegel:
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

    def is_mozaiek_type_present(self, type) -> bool:
        return isinstance(self, type)

    def check(self, omringd_door: pd.DataFrame) -> None:
        raise NotImplementedError()

    def get_mozk_perc_str(self) -> str:
        return ""

    @property
    def evaluation(self) -> MaybeBoolean:
        return self.cached_evaluation

    def __str__(self):
        raise NotImplementedError()


class NietGeimplementeerdeMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "NietGeimplementeerdeMozaiekregel"
    cached_evaluation: MaybeBoolean = MaybeBoolean.CANNOT_BE_AUTOMATED

    def check(self, omringd_door: pd.DataFrame) -> None:
        assert self.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED

    def __str__(self):
        return "Niet geautomatiseerde mozaiekregel: zie definitietabel."


class GeenMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "GeenMozaiekregel"
    cached_evaluation: MaybeBoolean = MaybeBoolean.TRUE

    def check(self, omringd_door: pd.DataFrame) -> None:
        assert self.cached_evaluation == MaybeBoolean.TRUE

    def __str__(self):
        return "Geen mozaiekregel (altijd waar)"


class StandaardMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "StandaardMozaiekregel"
    kwalificerend_habtype: str
    ook_mozaiekvegetaties: bool
    alleen_goede_kwaliteit: bool
    ook_als_rand_langs: bool

    # Uitgesplits in SBB en VvN lijsten voor (de)serializatie
    kwalificerende_SBB: List[SBB] = []
    kwalificerende_VvN: List[VvN] = []
    tegengekomen_kwal_SBB: List[SBB] = []
    tegengekomen_kwal_VvN: List[VvN] = []

    mozk_perc_tuples: List[MozkPercTuple] = []

    cached_evaluation: MaybeBoolean = MaybeBoolean.POSTPONE

    def determine_kwalificerende_vegtypen(self, deftabel_section: pd.DataFrame) -> None:
        # assert columns Habitattype, SBB and VvN are present
        assert all(
            col in deftabel_section.columns for col in ["Habitattype", "SBB", "VvN"]
        ), "Habitattype, SBB and VvN columns not all found in deftabel_section in determine_valid_vegtypen"

        assert all(
            deftabel_section.Habitattype == self.kwalificerend_habtype
        ), f"Not all Habitattype values are the expected {self.kwalificerend_habtype} in deftabel_section in determine_valid_vegtypen"

        # Casten naar list voor (de)serializatie
        self.kwalificerende_SBB = list(
            {
                vegtype
                for vegtype in deftabel_section.SBB.to_list()
                if vegtype is not None
            }
        )

        self.kwalificerende_VvN = list(
            {
                vegtype
                for vegtype in deftabel_section.VvN.to_list()
                if vegtype is not None
            }
        )

    def check(self, omringd_door: pd.DataFrame) -> None:
        """
        Checkt of er aan de mozaiekregel wordt voldaan adhv een omringd_door DataFrame met kolommen

            ElmID | habtype | kwaliteit | vegtypen | complexdeel_percentage | omringing_percentage
            Er is een rij voor ieder complexdeel in de omliggende vlakken.

        De benodigde gegevens (omringings% kwalificerende vlakken en omringings% HXXXX)
        om tot een truth value te komen worden door _bepaal_kwalificerende_en_HXXXX_omringing()
        onttrokken aan de omringd_door df.

        Vult ook de tegengekomen_kwal_vegtypen en mozk_perc_dict in.
        """
        assert set(omringd_door.columns).issuperset(
            {
                "ElmID",
                "habtype",
                "kwaliteit",
                "vegtypen",
                "complexdeel_percentage",
                "omringing_percentage",
            }
        ), "Not all expected columns found in omringd_door in mozaiekregel.check"

        assert (
            not self.ook_mozaiekvegetaties or self.kwalificerende_vegtypen is not None
        ), "kwalificerende_vegtypen not set in mozaiekregel.check"

        threshold = (
            self.mozaiek_threshold
            if not self.ook_als_rand_langs
            else self.mozaiek_als_rand_threshold
        )

        self._vul_mozk_perc_dict(omringd_door)

        (
            omringing_kwal_vlakken,
            omringing_HXXXX,
            tegengekomen_kwal_vegtypen,
        ) = self._bepaal_kwalificerende_en_HXXXX_omringing(omringd_door)

        self._vul_tegengekomen_kwal_SBB_VvN(tegengekomen_kwal_vegtypen)

        if omringing_kwal_vlakken >= threshold:
            self.cached_evaluation = MaybeBoolean.TRUE
            return

        # Als de totale omringing van kwalificerende vlakken + HXXXX voldoende is, kan deze
        # in volgende ronden nog TRUE worden, dus voor nu dan POSTPONE
        if omringing_kwal_vlakken + omringing_HXXXX >= threshold:
            self.cached_evaluation = MaybeBoolean.POSTPONE
            return

        self.cached_evaluation = MaybeBoolean.FALSE

    def _vul_mozk_perc_dict(self, omringd_door: pd.DataFrame) -> None:
        """
        Vult de mozk_perc_dict met keys (habtype, kwaliteit) en values (omringing percentage)

        Is gescheiden van _bepaal_kwalificerende_en_HXXXX_omringing om de logica netter te houden
        """
        mozk_perc_dict = defaultdict(int)

        grouped_by_vlak = omringd_door.groupby("ElmID")

        for _, vlak_group in grouped_by_vlak:
            assert (
                len(vlak_group.omringing_percentage.unique()) == 1
            ), f"Omringing percentage is niet hetzelfde voor alle complexdelen in vlak met ElmID {vlak_group.ElmID.iloc[0]}"

            grouped_by_habtype = vlak_group.groupby("habtype")
            for habtype, habtype_group in grouped_by_habtype:
                bedekking_goed_habtype = habtype_group[
                    habtype_group.kwaliteit == Kwaliteit.GOED
                ].complexdeel_percentage.sum()

                if bedekking_goed_habtype >= self.mozaiek_minimum_bedekking:
                    mozk_perc_dict[(habtype, Kwaliteit.GOED)] += habtype_group.iloc[
                        0
                    ].omringing_percentage
                    continue

                bedekking_matig_habtype = habtype_group.complexdeel_percentage.sum()
                if bedekking_matig_habtype >= self.mozaiek_minimum_bedekking:
                    if habtype in ["H0000", "HXXXX"]:
                        # H0000 en HXXXX hebben altijd kwaliteit NVT
                        mozk_perc_dict[(habtype, Kwaliteit.NVT)] += habtype_group.iloc[
                            0
                        ].omringing_percentage
                    else:
                        mozk_perc_dict[
                            (habtype, Kwaliteit.MATIG)
                        ] += habtype_group.iloc[0].omringing_percentage

        # We slaan dit op als tuples ipv gewoon als de dict zodat we mozaiekregels kunnen serializen
        self.mozk_perc_tuples = []

        for (habtype, kwaliteit), perc in mozk_perc_dict.items():
            self.mozk_perc_tuples.append(
                MozkPercTuple(habtype=habtype, kwaliteit=kwaliteit, percentage=perc)
            )

    def _vul_tegengekomen_kwal_SBB_VvN(
        self, tegengekomen_vegtypen: Set[Union[SBB, VvN]]
    ):
        # Casten naar list voor (de)serializatie
        self.tegengekomen_kwal_SBB = list(
            {vegtype for vegtype in tegengekomen_vegtypen if isinstance(vegtype, SBB)}
        )
        self.tegengekomen_kwal_VvN = list(
            {vegtype for vegtype in tegengekomen_vegtypen if isinstance(vegtype, VvN)}
        )

    def _bepaal_kwalificerende_en_HXXXX_omringing(
        self, omringd_door: pd.DataFrame
    ) -> Tuple[NumberType, NumberType, Set[Union[SBB, VvN]]]:
        """
        Bepaalt dmv _bepaal_kwalificerende_en_HXXXX_bedekking() per vlak het bedekkings% kwalificerende
        complexdelen en het bedekkings% HXXXX complexdelen. Hiermee wordt bepaald of het vlak telt als een
        kwalificerend vlak, als een HXXXX vlak, of als geen van beide, en wordt het omringingspercentage
        van het vlak opgeteld bij het corresponderende lopende totaal (omringing_kwal_vlakken, omringing_HXXXX, of nergens).

        Ook worden de tegengekomen kwalificerende vegetatietypen geaggeregeerd ter communicatie naar de gebruiker.
        """
        omringing_kwal_vlakken = 0
        omringing_HXXXX = 0
        tegengekomen_kwal_vegtypen = set()

        grouped_by_vlak = omringd_door.groupby("ElmID")

        for _, vlak_group in grouped_by_vlak:
            assert (
                len(vlak_group.omringing_percentage.unique()) == 1
            ), f"Omringing percentage is niet hetzelfde voor alle complexdelen in vlak met ElmID {vlak_group.ElmID.iloc[0]}"

            (
                bedekking_kwal_complexdelen,
                bedekking_HXXXX,
                tegengekomen_kwal_vegtypen_vlak,
            ) = self._bepaal_kwalificerende_en_HXXXX_bedekking(vlak_group)

            # Bijhouden welke vegetatietypen als kwalificerend zijn gerekend
            tegengekomen_kwal_vegtypen.update(tegengekomen_kwal_vegtypen_vlak)

            # Als we al over de threshold zitten, kunnen we stoppen met
            # tellen en dit vlak zien als kwalificerend
            if bedekking_kwal_complexdelen >= self.mozaiek_minimum_bedekking:
                omringing_kwal_vlakken += vlak_group.iloc[0].omringing_percentage
                continue

            # Als de totale bedekking kwalificerende complexdelen + HXXXX bedekking meer is dan
            # de minimale bedekkingsthreshold, zou dit vlak in volgende ronden alsnog kunnen gaan kwalificeren
            # en kunnen we dit vlak zien als een HXXXX vlak
            if (
                bedekking_HXXXX + bedekking_kwal_complexdelen
                > self.mozaiek_minimum_bedekking
            ):
                omringing_HXXXX += vlak_group.iloc[0].omringing_percentage
                continue

        return (omringing_kwal_vlakken, omringing_HXXXX, tegengekomen_kwal_vegtypen)

    def _bepaal_kwalificerende_en_HXXXX_bedekking(
        self, vlak_group: pd.DataFrame
    ) -> Tuple[NumberType, NumberType, Set[Union[SBB, VvN]]]:
        """
        Bepaalt voor een vlak wat de bedekking is van kwalificerende complexdelen en HXXXX complexdelen.

        Ook houdt het bij welke kwalificerende vegetatietypen tegengekomen zijn.
        """
        bedekking_kwal_complexdelen = 0
        bedekking_HXXXX = 0
        tegengekomen_kwal_vegtypen = set()

        # NOTE: Enkele van de volgende checks kunnen mogelijk geoptimaliseerd worden
        #       door ze te vervangen voor set operaties (set.issubset/set.intersection etc)
        for row in vlak_group.itertuples():
            if (
                # Als het habitattype matcht en er wordt aan de kwaliteitseisen voldaan
                row.habtype == self.kwalificerend_habtype
                and (row.kwaliteit == Kwaliteit.GOED or not self.alleen_goede_kwaliteit)
            ) or (
                # Of als de mozaiekvegetaties ook toegestaan zijn en daar is een match
                self.ook_mozaiekvegetaties
                and any(
                    vegtype in self.kwalificerende_vegtypen for vegtype in row.vegtypen
                )
            ):
                # Dan tellen we het percentage van het complexdeel mee
                bedekking_kwal_complexdelen += row.complexdeel_percentage
                tegengekomen_kwal_vegtypen.update(
                    [
                        vegtype
                        for vegtype in row.vegtypen
                        if vegtype in self.kwalificerende_vegtypen
                    ]
                )

            if row.habtype == "HXXXX":
                bedekking_HXXXX += row.complexdeel_percentage
                continue

        return (
            bedekking_kwal_complexdelen,
            bedekking_HXXXX,
            tegengekomen_kwal_vegtypen,
        )

    def __str__(self):
        complete_string = f"{'als rand langs ' if self.ook_als_rand_langs else ''}"
        complete_string += f"{'zelfstndg' if not self.ook_mozaiekvegetaties else 'zelfstndg/mozkveg van'} "
        complete_string += f"{'G' if self.alleen_goede_kwaliteit else 'G/M'} "
        complete_string += f"{self.kwalificerend_habtype}"
        return complete_string

    def get_mozk_perc_str(self) -> str:
        """
        Geeft de string voor in het _MozkPerc{i} veld in de output.
        Als dit een mozaiekregel is die ook mozaiekvegetaties accepteerd, worden
        alle gevonden kwalificerende vegetatietypen ook weergegeven.
        """
        mozk_percs_str = self._mozk_perc_dict_to_str()
        if len(self.tegengekomen_kwal_vegtypen) > 0:
            mozk_percs_str += " " + self._tegengekomen_kwal_vegtypen_to_str()
        return mozk_percs_str

    def _mozk_perc_dict_to_str(self) -> str:
        """
        Vertaald de mozk_perc_dict naar een string

        {('H1234', Kwaliteit.GOED): 50, ('H4321', Kwaliteit.MATIG): 50}
        "50% goed H1234, 50% matig H4321."
        """
        kwal_strs = {
            Kwaliteit.GOED: "goed ",
            Kwaliteit.MATIG: "matig ",
            Kwaliteit.NVT: "",
        }
        return (
            ", ".join(
                [
                    f"{percentage:.2f}% {kwal_strs[kwaliteit]}{habtype}"
                    for (habtype, kwaliteit, percentage) in self.mozk_perc_tuples
                ]
            )
            + "."
            if len(self.mozk_perc_tuples) > 0
            else ""
        )

    def _tegengekomen_kwal_vegtypen_to_str(self) -> str:
        """
        Zet de tegengekomen_kwal_vegtypen om naar een string

        {SBB('1a1a'), SBB('2a4'), VvN('3ab3c')}
        "Mozaiekvegetatietypen: 1a1a (SBB), 2a4 (SBB), 3ab3c (VvN)."
        """
        vegtypen_str = "Mozaiekvegetatietypen: "
        vegtypen_str += ", ".join(
            [
                f"{str(vegtype)} ({'SBB' if isinstance(vegtype, SBB) else 'VvN'})"
                for vegtype in self.tegengekomen_kwal_vegtypen
            ]
        )
        return vegtypen_str + "."

    @property
    def kwalificerende_vegtypen(self) -> Set[Union[SBB, VvN]]:
        return self.kwalificerende_SBB + self.kwalificerende_VvN

    @property
    def tegengekomen_kwal_vegtypen(self) -> Set[Union[SBB, VvN]]:
        return self.tegengekomen_kwal_SBB + self.tegengekomen_kwal_VvN


def make_buffered_boundary_overlay_gdf(
    gdf: gpd.GeoDataFrame,
    buffer: Number = 0.1,
) -> Union[None, gpd.GeoDataFrame]:
    """
    Trekt om elk vlak met een mozaiekregel een lijn met afstand "buffer" tot het vlak.
    Deze lijnen worden vervolgens over de originele gdf gelegd en opgeknipt per vlak waar ze over heen liggen.
    Elke sectie opgeknipte lijn krijgt mee hoeveel procent van de totale lijn het is.
    Deze "overlay gdf" wordt vervolgens teruggegeven.
    """
    if buffer < 0:
        raise ValueError(f"Buffer moet positief zijn, maar is {buffer}")

    if buffer == 0:
        logging.warning("Buffer is 0. Dit kan leiden tot onverwachte resultaten.")

    assert (
        "ElmID" in gdf.columns
    ), f"ElmID niet gevonden in gdf bij make_buffered_boundary_overlay_gdf"

    mozaiek_present = gdf.HabitatVoorstel.apply(
        lambda voorstellen: any(
            not isinstance(voorstel.mozaiek, GeenMozaiekregel)
            for sublist in voorstellen
            for voorstel in sublist
        )
    )

    if not mozaiek_present.any():
        return None

    # Eerst trekken we een lijn om alle shapes met mozaiekregels
    buffered_boundary = (
        gdf[mozaiek_present].buffer(buffer).boundary.to_frame(name="geometry")
    )
    assert buffered_boundary.crs == gdf.crs

    buffered_boundary["buffered_ElmID"] = gdf["ElmID"]
    buffered_boundary["full_line_length"] = buffered_boundary.length

    # Dan leggen we alle lijnen over de originele gdf
    only_needed_cols = gdf[["ElmID", "geometry"]]
    overlayed = gpd.overlay(
        buffered_boundary, only_needed_cols, how="union", keep_geom_type=True
    )
    # We droppen alle lijnen die niet over een vlak liggen
    overlayed = overlayed.dropna(subset=["ElmID"])
    overlayed["omringing_percentage"] = (
        overlayed.length / overlayed.full_line_length
    ) * 100

    # Geometry is niet meer nodig hierna
    return overlayed.drop(columns=["geometry"])


def construct_elmid_omringd_door_gdf(
    augmented_overlayed: pd.DataFrame,
) -> Optional[pd.DataFrame]:
    """
    ### Ontvangt een gdf met
        buffered_ElmID | full_line_length | ElmID | omringing_percentage | VegTypeInfo | HabitatKeuze

    Hierin is aangegeven voor ieder vlak (buffered_ElmID) door welke vlakken deze omgringd word (ElmID),
    samen met info over de omringing (full_line_length, omringing_percentage) en de habitatkeuzes/vegtypen
    van de omliggende vlakken.

    ### Maakt hiervan een gdf met
        buffered_ElmID | ElmID | habtype | vegtypen | complexdeel_percentage | omringing_percentage

    Elk complexdeel in alle vlakken rondom een buffered_ElmID krijgt een rij in de gdf
    met daarin het habitattype, de vegetatietypen en het percentage van het complexdeel.
    omringing_percentage is hetzelfde voor elk complexdeel binnen een ElmID
    """
    expected_cols = [
        "buffered_ElmID",
        "full_line_length",
        "ElmID",
        "omringing_percentage",
        "VegTypeInfo",
        "HabitatKeuze",
    ]
    assert all(
        col in augmented_overlayed.columns for col in expected_cols
    ), f"Niet alle kolommen {expected_cols} gevonden in augmented_overlayed bij construct_elmid_omringd_door_gdf"

    def expand_habkeuze_vegtypeinfo_columns(
        row: pd.Series,
    ) -> pd.DataFrame:
        """
        ### Ontvangt steeds een rij met
            buffered_ElmID | full_line_length | ElmID | omringing_percentage | VegTypeInfo | HabitatKeuze

        ### En trekt uit ieder VegTypeInfo/HabitatKeuze-paar de info om te krijgen
            buffered_ElmID | ElmID | habtype | kwaliteit | vegtypen | complexdeel_percentage | omringing_percentage
        """
        assert len(row.HabitatKeuze) == len(
            row.VegTypeInfo
        ), "HabitatKeuze en VegTypeInfo moeten even lang zijn"

        return pd.DataFrame(
            {
                "buffered_ElmID": row.buffered_ElmID,
                "ElmID": row.ElmID,
                "habtype": [
                    keuze.habtype if keuze is not None else "HXXXX"
                    for keuze in row.HabitatKeuze
                ],
                "kwaliteit": [
                    keuze.kwaliteit if keuze is not None else Kwaliteit.NVT
                    for keuze in row.HabitatKeuze
                ],
                "vegtypen": [info.VvN + info.SBB for info in row.VegTypeInfo],
                "complexdeel_percentage": [info.percentage for info in row.VegTypeInfo],
                "omringing_percentage": [row.omringing_percentage]
                * len(row.HabitatKeuze),
            }
        )

    result = augmented_overlayed.apply(expand_habkeuze_vegtypeinfo_columns, axis=1)

    if len(result) == 0:
        return None

    return pd.concat(result.values).reset_index(drop=True)


def is_mozaiek_type_present(
    voorstellen: Union[List[List["HabitatVoorstel"]], List["HabitatVoorstel"]],
    mozaiek_type: MozaiekRegel,
) -> bool:
    """
    Geeft True als er in de lijst met habitatvoorstellen eentje met een mozaiekregel van mozaiek_type is
    """
    # Als we een lijst van lijsten hebben, dan flattenen we die
    if any(isinstance(i, list) for i in voorstellen):
        voorstellen = [item for sublist in voorstellen for item in sublist]

    return any(
        [
            (voorstel.mozaiek.is_mozaiek_type_present(mozaiek_type))
            for voorstel in voorstellen
        ]
    )
