import logging
from collections import defaultdict
from pathlib import Path
from typing import ClassVar, List, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
from typing_extensions import Literal, Self

from veg2hab import vegetatietypen
from veg2hab.access_db import read_access_tables
from veg2hab.bronnen import FGR, LBK, Bodemkaart, OudeBossenkaart
from veg2hab.criteria import (
    BodemCriterium,
    FGRCriterium,
    LBKCriterium,
    OudeBossenCriterium,
    is_criteria_type_present,
)
from veg2hab.enums import KarteringState, KeuzeStatus, Kwaliteit, WelkeTypologie
from veg2hab.functionele_samenhang import apply_functionele_samenhang
from veg2hab.habitat import (
    HabitatKeuze,
    HabitatVoorstel,
    calc_nr_of_unresolved_habitatkeuzes_per_row,
    rank_habitatkeuzes,
    try_to_determine_habkeuze,
)
from veg2hab.io.common import Interface
from veg2hab.mozaiek import (
    construct_elmid_omringd_door_gdf,
    make_buffered_boundary_overlay_gdf,
)
from veg2hab.vegtypeinfo import VegTypeInfo


def ingest_vegtype(
    gdf: gpd.GeoDataFrame,
    SBB_cols: List[str],
    VvN_cols: List[str],
    rVvN_cols: List[str],
    perc_cols: List[str],
) -> pd.Series:
    """
    Leest de vegetatietypen van een vlak in en maakt er een lijst van VegTypeInfo objecten van
    Vlakken zonder percentage
    """
    # Validatie
    for cols in [SBB_cols, VvN_cols, rVvN_cols]:
        if len(cols) != 0 and len(cols) != len(perc_cols):
            raise ValueError(
                f"Het aantal vegtype kolommen (nu {len(cols)}) moet 0 zijn of gelijk zijn aan de lengte van perc_col ({len(perc_cols)})"
            )

    assert (
        len(SBB_cols) + len(VvN_cols) + len(rVvN_cols) > 0
    ), "Er moet een SBB, VvN of rVvN kolom zijn"

    # Inlezen
    if len(SBB_cols) == 0:
        SBB_cols = [None] * len(perc_cols)
    if len(VvN_cols) == 0:
        VvN_cols = [None] * len(perc_cols)
    if len(rVvN_cols) == 0:
        rVvN_cols = [None] * len(perc_cols)

    def _row_to_vegtypeinfo_list(row: gpd.GeoSeries) -> List[VegTypeInfo]:
        vegtype_list = []
        for sbb_col, vvn_col, rVvN_col, perc_col in zip(
            SBB_cols, VvN_cols, rVvN_cols, perc_cols
        ):
            # Als er geen percentage is, willen we ook geen VegTypeInfo,
            # dus slaan we deze over
            if pd.isnull(row[perc_col]) or row[perc_col] == 0:
                continue

            # Als er geen vegtypen zijn, willen we ook geen VegTypeInfo,
            # dus slaan we deze over
            if (
                (pd.isnull(row[sbb_col]) if sbb_col else True)
                and (pd.isnull(row[vvn_col]) if vvn_col else True)
                and (pd.isnull(row[rVvN_col]) if rVvN_col else True)
            ):
                continue

            vegtypeinfo = VegTypeInfo.from_str_vegtypes(
                row[perc_col],
                VvN_strings=[row[vvn_col]] if vvn_col else [],
                SBB_strings=[row[sbb_col]] if sbb_col else [],
                rVvN_strings=[row[rVvN_col]] if rVvN_col else [],
            )

            vegtype_list.append(vegtypeinfo)
        if len(vegtype_list) == 0:
            return [VegTypeInfo(percentage=100, SBB=[], VvN=[], rVvN=[])]
        return vegtype_list

    return gdf.apply(_row_to_vegtypeinfo_list, axis=1)


def fill_in_percentages(
    row: gpd.GeoSeries,
    vegtype_col_format: Literal["single", "multi"],
    perc_col: Union[str, List[str]],
    SBB_col: Union[str, List[str], None] = None,
    VvN_col: Union[str, List[str], None] = None,
    rVvN_col: Union[str, List[str], None] = None,
) -> gpd.GeoSeries:
    """
    Vult percentages in voor een rij. Ieder vegetatietype krijgt een percentage van 100/n_vegtypen.
    """
    assert (
        VvN_col is not None or SBB_col is not None or rVvN_col is not None
    ), "Er moet een SBB of VvN kolom zijn"

    assert vegtype_col_format == "multi"

    # Uitzoeken hoeveel vegtypen er zijn
    vvn_present = row[VvN_col].notna().reset_index(drop=True) if VvN_col else False
    sbb_present = row[SBB_col].notna().reset_index(drop=True) if SBB_col else False
    rvvn_present = row[rVvN_col].notna().reset_index(drop=True) if rVvN_col else False
    vegtype_present = vvn_present | sbb_present | rvvn_present
    n_vegtypen = vegtype_present.sum()

    # Percentages berekenen
    if n_vegtypen == 0:
        percentages = [0] * len(vegtype_present)
    else:
        percentages = [100 / n_vegtypen] * n_vegtypen + [0] * (
            len(vegtype_present) - n_vegtypen
        )

    # Percentages toekennen
    for perc_colname, percentage in zip(perc_col, percentages):
        row[perc_colname] = percentage

    return row


def sorteer_vegtypeinfos_en_habkeuzes_en_voorstellen(
    row: gpd.GeoSeries,
) -> gpd.GeoSeries:
    """
    Habitatkeuzes horen op een vaste volgorde: Eerst alle niet-H0000, dan op percentage, dan op kwaliteit
    Deze method ordent de Habitatkeuzes en zorgt ervoor dat de bij elke keuze horende VegTypeInfos/HabitatVoorstellen ook op de juiste volgorde worden gezet

    Voorbeeldje (zonder Voorstellen voor het gemak):
    Voor:
        HabitatKeuze: [HK1(H0000, 15%), HK2(H1234, 80%), HK3(H0000, 5%)]
        VegTypeInfo: [VT1(15%, SBB1), VT2(80%, SBB2), VT3(5%, SBB3)]
    Na:
        HabitatKeuze: [HK2(H1234, 80%), HK1(H0000, 15%), HK3(H0000, 5%)]
        VegTypeInfo: [VT2(80%, SBB2), VT1(15%, SBB1), VT3(5%, SBB3)]
    """
    if len(row["VegTypeInfo"]) == 0:
        # Er zijn geen vegtypeinfos, dus er is maar 1 habitatkeuze (H0000)
        return row

    keuze_vegtypeinfo_en_voorstellen = list(
        zip(row["HabitatKeuze"], row["VegTypeInfo"], row["HabitatVoorstel"])
    )
    # Sorteer op basis van de habitatkeuze (idx 0)
    sorted_keuze_vegtypeinfo_en_voorstellen = sorted(
        keuze_vegtypeinfo_en_voorstellen, key=rank_habitatkeuzes
    )

    row["HabitatKeuze"], row["VegTypeInfo"], row["HabitatVoorstel"] = zip(
        *sorted_keuze_vegtypeinfo_en_voorstellen
    )
    # Tuples uit zip omzetten naar lists
    row["HabitatKeuze"], row["VegTypeInfo"], row["HabitatVoorstel"] = (
        list(row["HabitatKeuze"]),
        list(row["VegTypeInfo"]),
        list(row["HabitatVoorstel"]),
    )
    return row


def hab_as_final_format(
    print_info: Tuple[HabitatKeuze, VegTypeInfo], idx: int, opp: float
) -> pd.Series:
    """
    Herformatteert een habitatkeuze en bijbehorende vegtypeinfo naar de kolommen zoals in het Gegevens Leverings Protocol
    """

    keuze, vegtypeinfo = print_info

    # Er is 1 HabitatVoorstel
    if len(keuze.habitatvoorstellen) == 1:
        if keuze.status in [
            KeuzeStatus.HABITATTYPE_TOEGEKEND,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
            KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
            KeuzeStatus.NIET_GEAUTOMATISEERD_VEGTYPE,
            KeuzeStatus.MINIMUM_OPP_NIET_GEHAALD,
            KeuzeStatus.HANDMATIG_TOEGEKEND,
        ]:
            voorstel = keuze.habitatvoorstellen[0]
            series_dict = {
                f"Habtype{idx}": keuze.habtype,
                f"Perc{idx}": vegtypeinfo.percentage,
                f"Opp{idx}": opp * (vegtypeinfo.percentage / 100),
                f"Kwal{idx}": keuze.kwaliteit.as_letter(),
                f"_V2H_bronnen_info{idx}": keuze.info,
                f"_Mits_info{idx}": keuze.mits_info,
                f"_Mozk_info{idx}": keuze.mozaiek_info,
                f"_MozkPerc{idx}": voorstel.mozaiek.get_mozk_perc_str(),
                f"VvN{idx}": ", ".join([str(code) for code in vegtypeinfo.VvN]),
                f"SBB{idx}": ", ".join([str(code) for code in vegtypeinfo.SBB]),
                f"_Status{idx}": str(keuze.status),
                f"_Uitleg{idx}": keuze.status.toelichting,
                f"_VvNdftbl{idx}": voorstel.get_VvNdftbl_str(),
                f"_SBBdftbl{idx}": voorstel.get_SBBdftbl_str(),
            }

            return pd.Series(series_dict)

        assert (
            False
        ), f"Er is 1 habitatvoorstel maar dat zou niet moeten kunnen in KeuzeStatus {keuze.status}"

    if keuze.status in [
        KeuzeStatus.HABITATTYPE_TOEGEKEND,
        KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN,
        KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN,
        KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
        KeuzeStatus.WACHTEN_OP_MOZAIEK,
        KeuzeStatus.HANDMATIG_TOEGEKEND,
        KeuzeStatus.MINIMUM_OPP_NIET_GEHAALD,
    ]:
        voorstellen = keuze.habitatvoorstellen
        series_dict = {
            f"Habtype{idx}": keuze.habtype,
            f"Perc{idx}": str(vegtypeinfo.percentage),
            f"Opp{idx}": str(opp * (vegtypeinfo.percentage / 100)),
            f"Kwal{idx}": keuze.kwaliteit.as_letter(),
            f"_V2H_bronnen_info{idx}": keuze.info,
            f"_Mits_info{idx}": keuze.mits_info,
            f"_Mozk_info{idx}": keuze.mozaiek_info,
            f"_MozkPerc{idx}": "\n".join(
                f"{nr + 1}. " + voorstel.mozaiek.get_mozk_perc_str()
                for nr, voorstel in enumerate(voorstellen)
            ),
            f"VvN{idx}": ", ".join(str(code) for code in vegtypeinfo.VvN),
            f"SBB{idx}": ", ".join(str(code) for code in vegtypeinfo.SBB),
            f"_Status{idx}": str(keuze.status),
            f"_Uitleg{idx}": keuze.status.toelichting,
            f"_VvNdftbl{idx}": "\n".join(
                f"{nr + 1}. " + voorstel.get_VvNdftbl_str()
                for nr, voorstel in enumerate(voorstellen)
            ),
            f"_SBBdftbl{idx}": "\n".join(
                f"{nr + 1}. " + voorstel.get_SBBdftbl_str()
                for nr, voorstel in enumerate(voorstellen)
            ),
        }

        return pd.Series(series_dict)

    assert (
        False
    ), f"hab_as_final_form voor KeuzeStatus {keuze.status} is niet geimplementeerd"


def build_aggregate_habtype_field(row: gpd.GeoSeries) -> str:
    """
    Maakt een samenvattende string van de habitattypen van een rij
    Hierbij worden de percentages van alle habtype/kwaliteit tuples bij elkaar
    Voorbeeld: 70% H1234 (G), 20% H0000, 10% HXXXX
    """
    habitatkeuzes = row["HabitatKeuze"]
    vegtypeinfos = row["VegTypeInfo"]

    assert len(habitatkeuzes) > 0, "Er moet minstens 1 habitatkeuze zijn"
    assert len(habitatkeuzes) == len(
        vegtypeinfos
    ), "Er moet voor iedere habitatkeuze een VegTypeInfo zijn"

    # Hierin krijgen we per (habtype, kwaliteit) tuple de som van de percentages
    aggregate = defaultdict(float)

    for keuze, info in zip(habitatkeuzes, vegtypeinfos):
        aggregate[(keuze.habtype, keuze.kwaliteit)] += info.percentage

    # Sorteren op (percentage, habtype, kwaliteit) zodat de string
    # altijd hetzelfde is bij dezelfde habtype/kwaliteit/percentage permutaties
    kwal_dict = {
        Kwaliteit.GOED: 0,
        Kwaliteit.MATIG: 1,
        Kwaliteit.NVT: 2,
    }
    aggregate = dict(
        sorted(
            aggregate.items(),
            key=(lambda item: (-item[1], item[0][0], kwal_dict[item[0][1]])),
        )
    )

    # Maken van alle losse strings
    aggregate_strings = []
    for key, value in aggregate.items():
        aggregate_string = f"{float(value)}%"
        if key[1] in [
            Kwaliteit.GOED,
            Kwaliteit.MATIG,
        ]:
            aggregate_string += f" ({key[1].value})"
        aggregate_string += f" {key[0]}"
        aggregate_strings.append(aggregate_string)

    return ", ".join(aggregate_strings)


def finalize_final_format(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Reorder de kolommen van een dataframe conform het Gegevens Leverings Protocol
    Resultaat zal zijn:
    Area   Opm   geometry   Habtype1   Perc1   Opp1   Kwal1   VvN1   SBB1   Habtype2   Perc2   Opp2...
    """
    new_columns = [
        "Area",
        "Opm",
        "Datum",
        "ElmID",
        "geometry",
        "_Samnvttng",
        "_LokVegTyp",
        "_LokVrtNar",
        "_state",
    ]
    n_habtype_blocks = len([i for i in gdf.columns if "Habtype" in i])
    for i in range(1, n_habtype_blocks + 1):
        new_columns = new_columns + [
            f"Habtype{i}",
            f"Perc{i}",
            f"Opp{i}",
            f"Kwal{i}",
            f"SBB{i}",
            f"VvN{i}",
            f"_SBBdftbl{i}",
            f"_VvNdftbl{i}",
            f"_Mits_info{i}",
            f"_V2H_bronnen_info{i}",
            f"_Mozk_info{i}",
            f"_MozkPerc{i}",
            f"_Status{i}",
            f"_Uitleg{i}",
        ]
    return gdf[new_columns]


def _combineer_twee_geodataframes(
    lage_prio: gpd.GeoDataFrame, hoge_prio: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Geometrische-operaties-hulpfunctie voor combine_karteringen

    Combineert twee geodataframes op basis van de geometrie; bij overlaps
    wordt de geometrie van lage_prio bijgesneden tot de overlap met hoge_prio

    De data van alle vlakken blijft onveranderd (zolang ze blijven bestaan)

                +-------+
    Lage_prio:  |   A   |
                +-------+
                    +-------+
    Hoge_prio:      |   B   |
                    +-------+
                +---+-------+
    Resultaat:  | A |   B   |
                +---+-------+
    """
    # Snij de geometrie van lage_prio bij tot de overlap met hoge_prio
    new_gdf = gpd.overlay(lage_prio, hoge_prio, how="difference")

    # Voeg de geometrie van hoge_prio toe
    new_gdf = new_gdf.append(hoge_prio)

    # Exploden eventuele multipolygons naar polygons
    new_gdf = new_gdf.reset_index(drop=True).explode(ignore_index=True)

    # Weglaten artefactvlakken/slivers
    threshold = (
        Interface.get_instance().get_config().combineer_karteringen_weglaten_threshold
    )
    new_gdf = new_gdf[new_gdf.area > threshold]

    return new_gdf


def fix_crs(
    gdf: gpd.GeoDataFrame, shape_path: Path = "onbekende locatie"
) -> gpd.GeoDataFrame:
    """
    Geeft voor gdfs zonder crs een warning en zet ze om naar EPSG:28992
    Zet gdfs met een andere crs dan EPSG:28992 om naar EPSG:28992
    """
    if gdf.crs is None:
        logging.warning(
            f"CRS van {shape_path} was None en is nu gelezen als EPSG:28992"
        )
        gdf = gdf.set_crs(epsg=28992)
    elif gdf.crs.to_epsg() != 28992:
        logging.info(
            f"CRS van {shape_path} was EPSG:{gdf.crs.to_epsg()} en is nu omgezet naar EPSG:28992"
        )
        gdf = gdf.to_crs(epsg=28992)
    return gdf


def _split_list_to_columns(
    row: Optional[pd.Series],
    new_col_prefix: str,
) -> pd.Series:
    """
    Splits een kolom met een lijst {col: [x1, x2, x3]} in n nieuwe kolommen {col1: x1, col2: x2, col3: x3}
    """
    result = pd.Series()
    if row is None:
        return result
    for idx, item in enumerate(row):
        result[f"{new_col_prefix}{idx+1}"] = item
    return result


def _single_to_multi(
    gdf: gpd.GeoDataFrame,
    SBB_col: Optional[str] = None,
    VvN_col: Optional[str] = None,
    rVvN_col: Optional[str] = None,
    split_char: Optional[str] = None,
    perc_col: Optional[str] = None,
) -> Tuple[gpd.GeoDataFrame, List[str], List[str], List[str]]:
    """
    Converteert een "single" kolomformat dataframe naar een "multi" kolomformat dataframe
    De nieuwe "multi" format kolommen heten SBB1/2/3/..., VvN1/2/3/... en perc1/2/3/...
    """
    # Uitvinden hoe veel kolommen er moeten komen
    assert SBB_col or VvN_col or rVvN_col, "Er moet een SBB of VvN of rVvN kolom zijn"
    if perc_col:
        n_cols_needed = (
            gdf[perc_col]
            .str.split(split_char)
            .apply(lambda x: 0 if x is None else len(x))
            .max()
        )
    else:
        if SBB_col:
            sbb_cols_needed = (
                gdf[SBB_col]
                .str.split(split_char)
                .apply(lambda x: 0 if x is None else len(x))
                .max()
            )
            n_cols_needed = sbb_cols_needed
        if VvN_col:
            vvn_cols_needed = (
                gdf[VvN_col]
                .str.split(split_char)
                .apply(lambda x: 0 if x is None else len(x))
                .max()
            )
            n_cols_needed = vvn_cols_needed
        if SBB_col and VvN_col:
            n_cols_needed = max(sbb_cols_needed, vvn_cols_needed)

        if rVvN_col:
            rvvn_cols_needed = (
                gdf[rVvN_col]
                .str.split(split_char)
                .apply(lambda x: 0 if x is None else len(x))
                .max()
            )
            n_cols_needed = rvvn_cols_needed

    for col in [SBB_col, VvN_col, rVvN_col, perc_col]:
        if col:
            new_columns = (
                gdf[col]
                .str.split(split_char)
                .apply(
                    _split_list_to_columns,
                    new_col_prefix=col,
                )
            )
            gdf = gdf.join(new_columns)

    # Kolomnamen moeten geupdated worden.
    if SBB_col:
        SBB_out = [f"{SBB_col}{idx+1}" for idx in range(n_cols_needed)]
        # Stel dat er max 3 VvN zijn en max 2 SBB, dan moet de SBB3 nog wel bestaan
        for col in SBB_out:
            if col not in gdf.columns:
                gdf[col] = None
    else:
        SBB_out = []

    if VvN_col:
        VvN_out = [f"{VvN_col}{idx+1}" for idx in range(n_cols_needed)]
        for col in VvN_out:
            if col not in gdf.columns:
                gdf[col] = None
    else:
        VvN_out = []

    if rVvN_col:
        rVvN_out = [f"{rVvN_col}{idx+1}" for idx in range(n_cols_needed)]
        for col in rVvN_out:
            if col not in gdf.columns:
                gdf[col] = None
    else:
        rVvN_out = []

    if perc_col:
        perc_out = [f"{perc_col}{idx+1}" for idx in range(n_cols_needed)]
        for col in perc_out:
            if col not in gdf.columns:
                gdf[col] = None
    else:
        perc_out = []

    return gdf, SBB_out, VvN_out, rVvN_out, perc_out


class Kartering:
    PREFIX_COLS: ClassVar[List[str]] = [
        # Met deze kolommen begint de dataframe
        "ElmID",
        "Area",
        "Datum",
        "Opm",
    ]
    POSTFIX_COLS: ClassVar[List[str]] = [
        # dit zijn de laatste paar kolommen voor de dataframe
        "_LokVegTyp",
        "_LokVrtNar",
        "_state",
        "geometry",
    ]
    VEGTYPE_COLS: ClassVar[List[str]] = [
        # kolommen voor de vegtype kartering
        "VegTypeInfo",
    ]
    HABTYPE_COLS: ClassVar[List[str]] = [
        # kolommen voor de habtype kartering
        "VegTypeInfo",
        "HabitatVoorstel",
        "HabitatKeuze",
    ]

    def __init__(self, gdf: gpd.GeoDataFrame):
        assert (
            len(gdf._state.unique()) == 1
        ), "Alle vlakken moeten dezelfde state hebben"
        state = gdf._state.iloc[0]

        if state in [KarteringState.PRE_WWL, KarteringState.POST_WWL]:
            expected_cols = self.PREFIX_COLS + self.VEGTYPE_COLS + self.POSTFIX_COLS
            if not all([col in gdf.columns for col in expected_cols]):
                raise ValueError(
                    f"Kolommen van kartering in state {state} kloppen niet"
                )

            self.gdf = gdf[
                self.PREFIX_COLS + self.VEGTYPE_COLS + self.POSTFIX_COLS
            ].copy()

            # Alle VegTypeInfo sorteren op percentage van hoog naar laag
            self.gdf["VegTypeInfo"] = self.gdf["VegTypeInfo"].apply(
                lambda x: sorted(x, key=lambda y: y.percentage, reverse=True)
            )

        elif state in [KarteringState.MITS_HABKEUZES, KarteringState.MOZAIEK_HABKEUZES]:
            expected_cols = self.PREFIX_COLS + self.HABTYPE_COLS + self.POSTFIX_COLS

            if not all([col in gdf.columns for col in expected_cols]):
                raise ValueError(
                    f"Kolommen van kartering in state {state} kloppen niet"
                )

            self.gdf = gdf[
                self.PREFIX_COLS + self.HABTYPE_COLS + self.POSTFIX_COLS
            ].copy()

        else:
            raise ValueError(
                f"Instantieren kartering met state {state} is niet ondersteund"
            )

        if not self.gdf["ElmID"].is_unique:
            raise ValueError("ElmID is niet uniek")

        # ArcGIS maakt van elke smaak int een Big Integer, wat het vervolgens niet op kan slaan in een GeoDataBase.
        # Dus we maken van ElmID een float64 (net als dat Area en andere getallen dat zijn).
        self.gdf.ElmID = self.gdf.ElmID.astype("float64")

    def check_state(self, *states: KarteringState):
        """
        Checkt of de kartering (een van de) de gegeven state(s) heeft
        Zo niet, dan raisen we een ValueError
        """
        assert (
            len(self.gdf._state.unique()) == 1
        ), "Alle vlakken moeten dezelfde state hebben"
        if not self.gdf._state.iloc[0] in states:
            raise ValueError(
                f"Kartering moet in een van de volgende states zijn: {states}"
            )

    def set_state(self, state: KarteringState) -> None:
        """
        Zet de state van de kartering
        """
        self.gdf["_state"] = state

    @classmethod
    def from_access_db(
        cls,
        shape_path: Path,
        shape_elm_id_column: str,
        access_mdb_path: Path,
        welke_typologie: WelkeTypologie = WelkeTypologie.SBB,
        opmerkingen_column: Optional[str] = None,
        datum_column: Optional[str] = None,
    ) -> Self:
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile en
        een access database die al is opgedeeld in losse csv bestanden.

        # .shp shp_elm_id_column -> ElmID in Element.csv voor intern_id -> Locatie in KarteringVegetatietype.csv voor Vegetatietype ->
        #      -> Code in Vegetatietype.csv voor SbbType -> Cata_ID in SsbType.csv voor Code (hernoemd naar Sbb)
        """
        assert welke_typologie in [
            WelkeTypologie.SBB,
            WelkeTypologie.rVvN,
        ], "Voor digitale standaard karteringen wordt enkel SBB of rVvN ondersteund"

        gdf = gpd.read_file(shape_path)

        gdf = fix_crs(gdf, shape_path)

        # Selecteren van kolommen
        columns_to_keep = [
            col
            for col in [
                shape_elm_id_column,
                opmerkingen_column,
                datum_column,
                "geometry",
            ]
            if col is not None
        ]
        gdf = gdf[columns_to_keep]

        # Als kolommen niet aanwezig zijn in de shapefile dan vullen we ze met None
        for old_col, new_col in [
            (opmerkingen_column, "Opm"),
            (datum_column, "Datum"),
        ]:
            if old_col is None:
                gdf[new_col] = None
            else:
                gdf = gdf.rename(columns={old_col: new_col})

        gdf["Area"] = gdf["geometry"].area
        gdf[
            "_LokVrtNar"
        ] = f"Lokale typologie is primair vertaald naar {welke_typologie.name}"

        element, veginfo_per_locatie = read_access_tables(
            access_mdb_path, welke_typologie
        )

        # Intern ID toevoegen aan de gdf
        try:
            gdf = gdf.merge(
                element,
                left_on=shape_elm_id_column,
                right_on="ElmID",
                how="left",
                validate="one_to_one",
            )
        except pd.errors.MergeError as e:
            message = f"Er is geen 1 op 1 relatie tussen {shape_elm_id_column} in de shapefile en ElmID in de Element.csv. "
            if not gdf[shape_elm_id_column].is_unique:
                dubbele_elmid = gdf[shape_elm_id_column][
                    gdf[shape_elm_id_column].duplicated()
                ].to_list()
                message += f"Er zitten {len(dubbele_elmid)} dubbelingen in de shapefile, bijvoorbeeld {shape_elm_id_column}: {dubbele_elmid[:10]}. "
            if not element.ElmID.is_unique:
                dubbele_elmid = element.ElmID[element.ElmID.duplicated()].to_list()[:10]
                message += f"Er zitten {len(dubbele_elmid)} dubbelingen in Element.csv, bijvoorbeeld ElmID: {dubbele_elmid[:10]}. "
            raise ValueError(message) from e

        # Joinen van de vegtypen aan de gdf
        gdf = gdf.merge(
            veginfo_per_locatie[["Locatie", "VegTypeInfo"]],
            left_on="intern_id",
            right_on="Locatie",
            how="left",
        )

        gdf = gdf.merge(
            veginfo_per_locatie[["Locatie", "_LokVegTyp"]],
            left_on="intern_id",
            right_on="Locatie",
            how="left",
        )

        # We laten alle NA vegtype-informatie vallen - dit kan komen door geometry die lijnen zijn in plaats van vormen,
        # maar ook aan ontbrekende waarden in een van de csv-bestanden.
        if gdf.VegTypeInfo.isnull().any():
            logging.warning(
                f"Er zijn {gdf.VegTypeInfo.isnull().sum()} vlakken zonder VegTypeInfo in {shape_path}. Deze worden verwijderd."
            )
            logging.warning(
                f"De eerste paar ElmID van de verwijderde vlakken zijn: {gdf[gdf.VegTypeInfo.isnull()].ElmID.head().to_list()}"
            )
            gdf = gdf.dropna(subset=["VegTypeInfo"])

        gdf["_state"] = KarteringState.PRE_WWL

        return cls(gdf)

    @classmethod
    def from_shapefile(
        cls,
        shape_path: Path,
        *,
        vegtype_col_format: Literal["single", "multi"],
        welke_typologie: WelkeTypologie,
        ElmID_col: Optional[str] = None,
        datum_col: Optional[str] = None,
        opmerking_col: Optional[str] = None,
        SBB_col: List[str],
        VvN_col: List[str],
        rVvN_col: List[str],
        split_char: Optional[str] = "+",
        perc_col: List[str] = [],
        lok_vegtypen_col: List[str] = [],
    ) -> Self:
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile.
        Input:
        - shape_path: het pad naar de shapefile
        - ElmID_col: de kolomnaam van de ElementID in de Shapefile; uniek per vlak
        - vegtype_col_format: "single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn
        - sbb_of_vvn: SBB, VvN, SBB_VvN of rVvN afhankelijk van welke vegetatietypen er uit de bron overgenomen moeten worden
        - datum_col: kolomnaam van de datum als deze er is
        - opmerking_col: kolomnaam van de opmerking als deze er is
        - VvN_col: kolomnaam van de VvN vegetatietypen als deze er is (bij single_col mag deze list maximaal lengte 1 hebben)
        - SBB_col: kolomnaam van de SBB vegetatietypen als deze er is (bij single_col mag deze list maximaal lengte 1 hebben)
        - split_char: karakter waarop de vegetatietypen gesplitst moeten worden (voor complexen (bv "16aa2+15aa")) (wordt bij mutli_col gebruikt om de kolommen te scheiden)
        - perc_col: kolomnaam van de percentage als deze er is (bij single_col mag deze list maximaal lengte 1 hebben))
        - lok_vegtypen_col: kolomnaam van de lokale vegetatietypen als deze er zijn (bij single_col mag deze list maximaal lengte 1 hebben)
        """
        # CONTROLEREN VAN DE INPUT
        if welke_typologie == WelkeTypologie.VvN:
            num_cols = len(VvN_col)
            if len(VvN_col) == 0:
                raise ValueError(
                    "VvN_col moet worden opgegeven als welke_typologie 'VvN' is."
                )
        elif welke_typologie == WelkeTypologie.SBB:
            num_cols = len(SBB_col)
            if len(SBB_col) == 0:
                raise ValueError(
                    "SBB_col moet worden opgegeven als welke_typologie 'SBB' is."
                )
        elif welke_typologie == WelkeTypologie.SBB_en_VvN:
            num_cols = len(VvN_col)
            if len(VvN_col) == 0 or len(SBB_col) == 0:
                raise ValueError(
                    "Zowel VvN_col als SBB_col moeten worden opgegeven als welke_typologie 'SBB en VvN' is."
                )
            if len(VvN_col) != len(SBB_col):
                raise ValueError(
                    "VvN_col en SBB_col moeten even lang zijn als welke_typologie 'SBB en VvN' is."
                )
        elif welke_typologie == WelkeTypologie.rVvN:
            num_cols = len(rVvN_col)
            if len(rVvN_col) == 0:
                raise ValueError(
                    "rVvN_col moet worden opgegeven als welke_typologie 'rVvN' is."
                )

        if vegtype_col_format == "single":
            if num_cols != 1:
                raise ValueError(
                    "Aantal kolommen moet 1 zijn bij vegtype_col_format == 'single'"
                )
        elif vegtype_col_format == "multi":
            if num_cols == 0:
                raise ValueError(
                    "Aantal kolommen moet groter dan 0 zijn bij vegtype_col_format == 'multi'"
                )

        if len(perc_col) != num_cols and len(perc_col) != 0:
            raise ValueError(
                "Aantal kolommen moet gelijk zijn tussen perc_col en SBB_col/VvN_col/rVvN_col"
            )

        if len(lok_vegtypen_col) != num_cols and len(lok_vegtypen_col) != 0:
            raise ValueError(
                "Aantal kolommen moet gelijk zijn tussen perc_col en lok_vegtypen_col"
            )

        # VALIDEREN, OPSCHONEN EN AANVULLEN VAN DE SHAPEFILE
        shapefile = gpd.read_file(shape_path)

        if ElmID_col and not shapefile[ElmID_col].is_unique:
            logging.warning(
                f"""De kolom {ElmID_col} bevat niet-unieke waarden in {shape_path}.
                Eerste paar dubbele waarden:
                {
                    shapefile[ElmID_col][shapefile[ElmID_col].duplicated()].head().to_list()
                }
                Er worden nieuwe waarden voor {ElmID_col} gemaakt en vanaf nu gebruikt.
                """
            )
            ElmID_col = None

        # Nieuwe ElmID kolom maken als dat nodig is
        if ElmID_col is None:
            ElmID_col = "ElmID"
            shapefile[ElmID_col] = range(len(shapefile))

        # Om niet bij splitten steeds "if split_char is not None:" te hoeven doen
        if split_char is None:
            split_char = "+"

        # Vastleggen lokale vegtypen voor in de output
        if len(lok_vegtypen_col) > 0:
            shapefile["_LokVegTyp"] = shapefile.apply(
                lambda row: ", ".join([str(row[col]) for col in lok_vegtypen_col]),
                axis=1,
            )
        else:
            shapefile[
                "_LokVegTyp"
            ] = "Geen kolommen opgegeven voor lokale vegetatietypen"

        # Selectie van de te bewaren kolommen
        cols = [col for col in [datum_col, opmerking_col] if col is not None] + [
            ElmID_col,
            "_LokVegTyp",
            "geometry",
        ]

        # Uitvinden welke vegtype kolommen er mee moeten
        cols += SBB_col + VvN_col + rVvN_col + perc_col
        if not all(col in shapefile.columns for col in cols):
            raise ValueError(
                f"Niet alle opgegeven kolommen ({cols}) gevonden in de shapefile kolommen ({shapefile.columns})"
            )
        gdf = shapefile[cols].copy()

        # Standardiseren van kolomnamen
        # Als er geen datum of opmerking kolom is, dan maken we die en vullen we deze met None
        if datum_col is None:
            datum_col = "Datum"
            gdf[datum_col] = None
        if opmerking_col is None:
            opmerking_col = "Opm"
            gdf[opmerking_col] = None

        gdf = gdf.rename(
            columns={ElmID_col: "ElmID", opmerking_col: "Opm", datum_col: "Datum"}
        )
        ElmID_col = "ElmID"
        opmerking_col = "Opm"
        datum_col = "Datum"

        gdf = fix_crs(gdf, shape_path)

        if vegtype_col_format == "single":
            gdf, SBB_col, VvN_col, rVvN_col, perc_col = _single_to_multi(
                gdf=gdf,
                SBB_col=None if len(SBB_col) == 0 else SBB_col[0],
                VvN_col=None if len(VvN_col) == 0 else VvN_col[0],
                rVvN_col=None if len(rVvN_col) == 0 else rVvN_col[0],
                split_char=split_char,
                perc_col=None if len(perc_col) == 0 else perc_col[0],
            )
            vegtype_col_format = "multi"

        # Opschonen
        if len(SBB_col) > 0:
            gdf[SBB_col] = gdf[SBB_col].apply(vegetatietypen.SBB.opschonen_series)

        if len(VvN_col) > 0:
            gdf[VvN_col] = gdf[VvN_col].apply(vegetatietypen.VvN.opschonen_series)

        if len(rVvN_col) > 0:
            gdf[rVvN_col] = gdf[rVvN_col].apply(vegetatietypen.rVvN.opschonen_series)

        # Standardiseren van kolomnamen
        gdf["Area"] = gdf["geometry"].area
        gdf[
            "_LokVrtNar"
        ] = f"Lokale typologie is primair vertaald naar {welke_typologie.value}."

        # Aangezien we de rVvN gaan verliezen in apply_wll(), zetten we deze in _LokVrtNar zodat
        # de gebruiker ze nog wel kan terugvinden
        if welke_typologie == WelkeTypologie.rVvN:
            gdf["_LokVrtNar"] = gdf[["_LokVrtNar"] + rVvN_col].apply(
                lambda row: row._LokVrtNar
                + " "
                + ", ".join([row[col] for col in rVvN_col if row[col]]),
                axis=1,
            )

        # Percentages invullen als die er niet zijn
        if len(perc_col) == 0:
            assert (
                vegtype_col_format == "multi"
            ), "vegtype_col_format should be (converted to) multi at this point"
            perc_col = [
                f"perc_{n}"
                for n in range(
                    max(
                        [
                            len(col)
                            for col in [SBB_col, VvN_col, rVvN_col]
                            if col is not None
                        ]
                    )
                )
            ]
            gdf = gdf.apply(
                lambda row: fill_in_percentages(
                    row, vegtype_col_format, perc_col, SBB_col, VvN_col, rVvN_col
                ),
                axis=1,
            )

        ###############
        ##### Inlezen van de vegetatietypen
        ###############

        gdf["VegTypeInfo"] = ingest_vegtype(
            gdf,
            SBB_col,
            VvN_col,
            rVvN_col,
            perc_col,
        )

        gdf["_state"] = KarteringState.PRE_WWL

        return cls(gdf)

    def apply_wwl(
        self, wwl: "WasWordtLijst", override_existing_VvN: bool = False
    ) -> None:
        """
        Past de was-wordt lijst toe op de kartering om VvN toe te voegen aan SBB-only karteringen
        """
        self.check_state(KarteringState.PRE_WWL)
        self.set_state(KarteringState.POST_WWL)

        # Als er rVvN aanwezig zijn
        if (
            self.gdf["VegTypeInfo"]
            .apply(lambda infos: any(len(info.rVvN) > 0 for info in infos))
            .any()
        ):
            self.gdf["VegTypeInfo"] = wwl.van_rVvN_naar_SBB_en_VvN(
                self.gdf["VegTypeInfo"]
            )
            return

        # Check dat er niet al VvN aanwezig zijn in de VegTypeInfo's
        # NOTE NOTE: Als we zowel SBB en VvN uit de kartering hebben, willen we
        #            dan nog wwl doen voor de SBB zonder al meegegeven VvN?
        VvN_already_present = self.gdf["VegTypeInfo"].apply(
            lambda infos: any(len(info.VvN) > 0 for info in infos)
        )
        if VvN_already_present.any() and not override_existing_VvN:
            logging.warning(
                "Er zijn al VvN aanwezig in de kartering. De was-wordt lijst wordt niet toegepast."
            )
            return

        self.gdf["VegTypeInfo"] = self.gdf["VegTypeInfo"].apply(
            wwl.toevoegen_VvN_aan_List_VegTypeInfo
        )

    @staticmethod
    def _vegtypeinfo_to_multi_col(vegtypeinfos: List[VegTypeInfo]) -> pd.Series:
        result = pd.Series(dtype="object")
        for idx, info in enumerate(vegtypeinfos, 1):
            result[f"EDIT_SBB{idx}"] = ",".join(
                str(sbb) for sbb in info.SBB
            )  # convert to pandas string..
            result[f"EDIT_VvN{idx}"] = ",".join(str(vvn) for vvn in info.VvN)
            result[f"EDIT_perc{idx}"] = info.percentage
        return result

    def to_editable_vegtypes(self) -> gpd.GeoDataFrame:
        self.check_state(KarteringState.POST_WWL)

        # rVvN karteringen moeten al omgezet zijn op dit punt
        assert (
            self.gdf["VegTypeInfo"]
            .apply(lambda infos: all(len(info.rVvN) == 0 for info in infos))
            .all()
        ), "Er zijn nog rVvN vegetatietypen aanwezig"

        # unpack the vegtypeinfo
        vegtypes_df = self.gdf["VegTypeInfo"].apply(self._vegtypeinfo_to_multi_col)
        str_columns = {
            name: "string"
            for name in vegtypes_df.columns
            if name.startswith("EDIT_SBB") or name.startswith("EDIT_VvN")
        }
        perc_columns = {
            name: float for name in vegtypes_df.columns if name.startswith("EDIT_perc")
        }
        vegtypes_df = vegtypes_df.astype({**str_columns, **perc_columns})
        vegtypes_df[list(str_columns.keys())] = vegtypes_df[
            list(str_columns.keys())
        ].replace("", pd.NA)

        # move and rename vegtype info column to the end
        gdf = self.gdf.rename(columns={"VegTypeInfo": "_VegTypeInfo"})
        gdf = pd.concat([gdf, vegtypes_df], axis=1)

        gdf["_VegTypeInfo"] = (
            gdf["_VegTypeInfo"].apply(VegTypeInfo.serialize_list).astype("string")
        )

        gdf["_state"] = gdf["_state"].apply(lambda x: x.value)

        column_order = [
            *self.PREFIX_COLS,
            *vegtypes_df.columns,
            "_VegTypeInfo",
            *self.POSTFIX_COLS,
        ]

        gdf = gdf[column_order]

        # for some dumb reason ARCGis handles columns that begin with a _ or a number
        # really badly.
        rename_cols = {
            col: "INTERN" + col for col in column_order if col.startswith("_")
        }
        gdf = gdf.rename(columns=rename_cols)

        return gdf

    @staticmethod
    def _multi_col_to_vegtype(row: pd.Series) -> List[VegTypeInfo]:
        result = []
        for idx in range(1, 100):  # arbitrary number
            sbb = row.get(f"EDIT_SBB{idx}", "")
            sbb = "" if pd.isnull(sbb) else str(sbb)
            vvn = row.get(f"EDIT_VvN{idx}", "")
            vvn = "" if pd.isnull(vvn) else str(vvn)
            perc = row.get(f"EDIT_perc{idx}", None)
            # if all are empty, we're done for this row
            if sbb == "" and vvn == "" and pd.isna(perc):
                break
            result.append(
                VegTypeInfo.from_str_vegtypes(
                    SBB_strings=sbb.split(","),
                    VvN_strings=vvn.split(","),
                    percentage=perc,
                )
            )
        else:
            raise ValueError("Er zijn te veel kolommen met SBB/VvN/percentage")

        return result

    @classmethod
    def from_editable_vegtypes(cls, gdf: gpd.GeoDataFrame) -> Self:
        rename_cols_intern = {
            col: col[len("INTERN") :]
            for col in gdf.columns
            if col.startswith("INTERN_")
        }
        gdf = gdf.rename(columns=rename_cols_intern)

        gdf["_VegTypeInfo"] = gdf["_VegTypeInfo"].apply(VegTypeInfo.deserialize_list)

        altered_vegtypes = gdf.apply(cls._multi_col_to_vegtype, axis=1)

        changes = gdf["_VegTypeInfo"] != altered_vegtypes
        if changes.any():
            logging.warning(
                f"Er zijn handmatige wijzigingen in de vegetatietypen. Deze worden overgenomen. Veranderde vlakken: ElmID={gdf['ElmID'][changes].to_list()}"
            )

        gdf["VegTypeInfo"] = altered_vegtypes
        gdf = gdf.drop(
            columns=[
                "_VegTypeInfo",
                *gdf.columns[gdf.columns.str.startswith(("SBB", "VvN", "perc"))],
            ]
        )

        gdf["_state"] = gdf["_state"].apply(KarteringState)

        kartering = cls(gdf)
        kartering.check_state(KarteringState.POST_WWL)

        return kartering

    @staticmethod
    def combineer_karteringen(karteringen: List[Self]) -> Self:
        """
        Accepteert een lijst met karteringen. Deze worden gecombineerd door ze
        op de volgorde in de lijst over elkaar heen te leggen.

        Data binnen de vlakken blijft gelijk, buiten dat er een nieuwe ElmID
        wordt gegenereerd en de oppervlakten (gdf.Area) opnieuw berekend worden

        Input:   [kart1, kart2, kart3]
                    +-------+
        kart1:      |   A   |
                    +-------+
                        +-------+
        kart2:          |   B   |
                        +-------+
                            +-------+
        kart3:              |   C   |
                            +-------+

                    +---+---+-------+
        Output:     | A | B |   C   |
                    +---+---+-------+
        """
        assert (
            len(karteringen) > 1
        ), "Er moeten minstens 2 karteringen zijn om te combineren"

        for kartering in karteringen:
            assert isinstance(
                kartering, Kartering
            ), "Alle elementen in karteringen moeten Karteringen zijn"
            kartering.check_state(KarteringState.POST_WWL)

        result = karteringen[0].gdf
        for kartering in karteringen[1:]:
            result = _combineer_twee_geodataframes(
                lage_prio=result,
                hoge_prio=kartering.gdf,
            )

        # Reset index en ElmID
        result = result.reset_index(drop=True)
        result["ElmID"] = range(len(result))

        # Oppervlakten kunnen veranderd zijn
        result["Area"] = result.geometry.area

        return Kartering(result)

    def apply_deftabel(self, dt: "DefinitieTabel") -> None:
        """
        Past de definitietabel toe op de kartering om habitatvoorstellen toe te voegen
        """
        self.check_state(KarteringState.POST_WWL)
        self.set_state(KarteringState.POST_DEFTABEL)

        self.gdf["HabitatVoorstel"] = self.gdf["VegTypeInfo"].apply(
            lambda infos: [dt.find_habtypes(info) for info in infos]
            if len(infos) > 0
            else [[HabitatVoorstel.H0000_no_vegtype_present()]]
        )

    def _check_mitsen(
        self, fgr: FGR, bodemkaart: Bodemkaart, lbk: LBK, obk: OudeBossenkaart
    ) -> None:
        """
        Checkt of de mitsen in de habitatvoorstellen van de kartering wordt voldaan.
        """
        self.check_state(KarteringState.MITS_HABKEUZES)

        # Deze dataframe wordt verrijkt met de info nodig om mitsen te checken.
        mits_info_df = gpd.GeoDataFrame(self.gdf.geometry)

        ### Bepaal waar meer informatie nodig is
        fgr_needed = self.gdf["HabitatVoorstel"].apply(
            is_criteria_type_present, args=(FGRCriterium,)
        )
        bodem_needed = self.gdf["HabitatVoorstel"].apply(
            is_criteria_type_present, args=(BodemCriterium,)
        )
        lbk_needed = self.gdf["HabitatVoorstel"].apply(
            is_criteria_type_present, args=(LBKCriterium,)
        )
        obk_needed = self.gdf["HabitatVoorstel"].apply(
            is_criteria_type_present, args=(OudeBossenCriterium,)
        )
        # mits_info_df heeft al een geometry, dus die hoeft niet toegevoegd (voor OverrideCriterium)

        ### Verrijken met de benodigde informatie (joins zijn op index)
        if fgr_needed.any():
            mits_info_df = mits_info_df.join(
                fgr.for_geometry(mits_info_df.loc[fgr_needed])
            )
        if lbk_needed.any():
            mits_info_df = mits_info_df.join(
                lbk.for_geometry(mits_info_df.loc[lbk_needed])
            )
        if bodem_needed.any():
            mits_info_df = mits_info_df.join(
                bodemkaart.for_geometry(mits_info_df.loc[bodem_needed])
            )
        if obk_needed.any():
            mits_info_df = mits_info_df.join(
                obk.for_geometry(mits_info_df.loc[obk_needed])
            )

        ### Mitsen checken
        for idx, row in self.gdf.iterrows():
            mits_info_row = mits_info_df.loc[idx]
            for voorstellen in row.HabitatVoorstel:
                for voorstel in voorstellen:
                    if voorstel.mits is None:
                        raise ValueError("Er is een habitatvoorstel zonder mits")
                    voorstel.mits.check(mits_info_row)

    def bepaal_mits_habitatkeuzes(
        self, fgr: FGR, bodemkaart: Bodemkaart, lbk: LBK, obk: OudeBossenkaart
    ) -> None:
        """
        Bepaalt voor complexdelen zonder mozaiekregels de habitatkeuzes
        HabitatKeuzes waar ook mozaiekregels mee gemoeid zijn worden uitgesteld tot in bepaal_mozaiek_habitatkeuzes
        """
        self.check_state(KarteringState.POST_DEFTABEL)
        self.set_state(KarteringState.MITS_HABKEUZES)

        assert isinstance(fgr, FGR), f"fgr moet een FGR object zijn, geen {type(fgr)}"
        assert isinstance(
            bodemkaart, Bodemkaart
        ), f"bodemkaart moet een Bodemkaart object zijn, geen {type(bodemkaart)}"
        assert isinstance(lbk, LBK), f"lbk moet een LBK object zijn, geen {type(lbk)}"

        self._check_mitsen(fgr, bodemkaart, lbk, obk)

        self.gdf["HabitatKeuze"] = self.gdf["HabitatVoorstel"].apply(
            lambda voorstellen: [
                try_to_determine_habkeuze(voorstel) for voorstel in voorstellen
            ]
        )

        # Vegtypeinfos en Habkeuzes sorteren op correcte outputvolgorde
        self.gdf = self.gdf.apply(
            sorteer_vegtypeinfos_en_habkeuzes_en_voorstellen, axis=1
        )

    def bepaal_mozaiek_habitatkeuzes(self, max_iter: int = 20) -> None:
        """
        Reviseert de habitatkeuzes op basis van mozaiekregels.
        """
        self.check_state(KarteringState.MITS_HABKEUZES)
        self.set_state(KarteringState.MOZAIEK_HABKEUZES)

        # We willen de habitatkeuzes die al bepaald zijn niet overschrijven
        self.gdf["HabitatKeuze"] = self.gdf["HabitatKeuze"].apply(
            lambda keuzes: [
                keuze
                if keuze.status
                in [KeuzeStatus.HANDMATIG_TOEGEKEND, KeuzeStatus.HABITATTYPE_TOEGEKEND]
                else None
                for keuze in keuzes
            ]
        )

        ### Verkrijgen overlay gdf
        # Hier staat in welke vlakken er voor hoeveel procent aan welke andere vlakken grenzen
        # Als er geen vlakken met mozaiekregels zijn of als deze vlakken allemaal nergens aan grenzen is overlayed None
        overlayed = make_buffered_boundary_overlay_gdf(self.gdf)

        for i in range(max_iter):
            keuzes_still_to_determine_pre = calc_nr_of_unresolved_habitatkeuzes_per_row(
                self.gdf
            )
            n_keuzes_still_to_determine_pre = keuzes_still_to_determine_pre.sum()

            #####
            # Mozaiekregels checken
            #####
            # We hoeven geen mozaiekdingen te doen als we geen vlakken met mozaiekregels hebben
            if overlayed is not None:
                # Vlakken waar alle HabitatKeuzes al bepaald zijn kunnen uit de mozaiekregel overlayed gdf
                finished_ElmID = self.gdf[
                    keuzes_still_to_determine_pre == 0
                ].ElmID.to_list()
                overlayed = overlayed[~overlayed.buffered_ElmID.isin(finished_ElmID)]

                # Mergen HabitatVoorstel met overlayed
                # Nu hebben we dus per mozaiekregelvlak voor hoeveel procent het aan
                # welke HabitatKeuzes en vegtypeinfos grenst
                augmented_overlayed = overlayed.merge(
                    self.gdf[["ElmID", "VegTypeInfo", "HabitatKeuze"]],
                    on="ElmID",
                    how="left",
                )

                # Dit pakken we verder uit zodat ieder complexdeel in ieder omringend vlak
                # een eigen regel heeft met daarin het habitattype, de vegtypen en het complexdeelpercentage
                elmid_omringd_door = construct_elmid_omringd_door_gdf(
                    augmented_overlayed
                )
                self._check_mozaiekregels(elmid_omringd_door)

            #####
            # Habitatkeuze proberen te bepalen
            #####

            self.gdf["HabitatKeuze"] = self.gdf[
                ["HabitatVoorstel", "HabitatKeuze"]
            ].apply(
                lambda row: [
                    keuze
                    if (
                        keuze is not None
                        and keuze.status == KeuzeStatus.HANDMATIG_TOEGEKEND
                    )
                    else try_to_determine_habkeuze(voorstel)
                    for keuze, voorstel in zip(row.HabitatKeuze, row.HabitatVoorstel)
                ],
                axis=1,
            )

            n_keuzes_still_to_determine_post = (
                calc_nr_of_unresolved_habitatkeuzes_per_row(self.gdf).sum()
            )

            logging.debug(
                f"Iteratie {i}: van {n_keuzes_still_to_determine_pre} naar {n_keuzes_still_to_determine_post} habitattypen nog te bepalen"
            )

            if (
                n_keuzes_still_to_determine_pre == n_keuzes_still_to_determine_post
                or n_keuzes_still_to_determine_post == 0
            ):
                break
        else:
            logging.warning(
                f"Maximaal aantal iteraties ({max_iter}) bereikt in de mozaiekregel loop."
            )

        # Of we hebben overal een keuze, of we komen niet verder met nog meer iteraties,
        # of we hebben max_iter bereikt

        if n_keuzes_still_to_determine_post > 0:
            logging.info(
                f"Er zijn nog {n_keuzes_still_to_determine_post} habitatkeuzes die niet bepaald konden worden."
            )

        assert (
            self.gdf.HabitatKeuze.apply(
                lambda keuzes: sum([keuze is None for keuze in keuzes])
            ).sum()
            == 0
        ), "Er zijn nog habitatkeuzes die niet behandeld zijn en nog None zijn na bepaal_habitatkeuzes"

        # Vegtypeinfos en Habkeuzes sorteren op correcte outputvolgorde
        self.gdf = self.gdf.apply(
            sorteer_vegtypeinfos_en_habkeuzes_en_voorstellen, axis=1
        )

    def _check_mozaiekregels(self, elmid_omringd_door: Optional[pd.DataFrame]) -> None:
        if elmid_omringd_door is None:
            return

        for row in self.gdf.itertuples():
            for idx, voorstel_list in enumerate(row.HabitatVoorstel):
                # Als er geen habitatkeuzes zijn (want geen vegtypen opgegeven),
                # dan hoeven we ook geen mozaiekregels te checken
                if len(row.HabitatKeuze) == 0:
                    continue

                # Als we voor deze voorstellen al een HabitatKeuze hebben hoeven
                # we niet weer de mozaiekregels te checken
                # TODO: Nu check ik hier heel handmatig of de keuze gemaakt is, en dat moet op dezelfde manier als in
                #       calc_nr_of_unresolved_habitatkeuzes_per_row() gedaan worden :/
                #       Dit kan netter, of dezelfde functie gebruiken of een extra kolommetje ofzo
                if (
                    row.HabitatKeuze[idx] is not None
                    and row.HabitatKeuze[idx].status != KeuzeStatus.WACHTEN_OP_MOZAIEK
                ):
                    continue

                relevant_subset = elmid_omringd_door[
                    elmid_omringd_door["buffered_ElmID"] == row.ElmID
                ]

                for voorstel in voorstel_list:
                    voorstel.mozaiek.check(relevant_subset)

    def functionele_samenhang(self) -> pd.DataFrame:
        """
        Past de habitatkeuzes aan volgens de regels van minimumoppervlak en functionele samenhang
        """
        self.check_state(KarteringState.MOZAIEK_HABKEUZES)
        self.set_state(KarteringState.FUNC_SAMENHANG)

        self.gdf = apply_functionele_samenhang(self.gdf)

    @staticmethod
    def _habkeuzes_to_multi_col(keuzes: List[HabitatKeuze]) -> pd.Series:
        result = {}
        for idx, keuze in enumerate(keuzes, 1):
            result.update(
                {
                    f"Habtype{idx}": keuze.habtype,
                    f"Kwal{idx}": keuze.kwaliteit.as_letter(),
                    f"_V2H_bronnen_info{idx}": keuze.info,
                }
            )
        return pd.Series(result)

    def to_editable_habtypes(self) -> gpd.GeoDataFrame:
        self.check_state(
            KarteringState.MITS_HABKEUZES,
            KarteringState.MOZAIEK_HABKEUZES,
            KarteringState.FUNC_SAMENHANG,
        )

        editable_habtypes = self.as_final_format()

        # Aanpasbare kolommen taggen we met een EDIT_
        editable_columns = ["Habtype", "Kwal", "Opm"]
        rename_final_format_edit_cols = {
            name: f"EDIT_{name}"
            for name in editable_habtypes.columns
            if (
                any(name.startswith(col) for col in editable_columns)
                and name[-1].isdigit()
            )
        }
        editable_habtypes = editable_habtypes.rename(
            columns=rename_final_format_edit_cols
        )

        # Kolommen die voor veg2hab nog van belang zijn taggen we INTERN_
        editable_habtypes["INTERN_VegTypeInfo"] = (
            self.gdf["VegTypeInfo"].apply(VegTypeInfo.serialize_list).astype("string")
        )
        editable_habtypes["INTERN_HabitatKeuze"] = (
            self.gdf["HabitatKeuze"].apply(HabitatKeuze.serialize_list).astype("string")
        )
        editable_habtypes["INTERN_HabitatVoorstel"] = (
            self.gdf["HabitatVoorstel"]
            .apply(HabitatVoorstel.serialize_list2)
            .astype("string")
        )

        # fill empty strings with pd.NA
        editable_habtypes = editable_habtypes.replace("", pd.NA)

        return editable_habtypes

    @staticmethod
    def _multi_col_to_habkeuze(row: pd.Series) -> List[Tuple[str, str]]:
        result = []
        for idx in range(1, 100):  # arbitrary number
            habtype = row.get(f"Habtype{idx}", None)
            habkeuze = row.get(f"Kwal{idx}", None)
            if habtype is None and habkeuze is None:
                break
            result.append((habtype, habkeuze))
        else:
            raise ValueError("Er zijn te veel kolommen met Habtype/Kwal")

        return result

    @classmethod
    def from_editable_habtypes(cls, gdf: gpd.GeoDataFrame) -> Self:
        # arcgis kan geen kolommen beginnend met een _ laten zien, dus de ervoor gezette f kan weer weg
        fix_arcgis_underscore = {
            col: col[len("f") :] for col in gdf.columns if col.startswith("f_")
        }
        gdf = gdf.rename(columns=fix_arcgis_underscore)

        # rename the INTERN columns
        rename_columns = {
            col: col[len("INTERN") :]
            for col in gdf.columns
            if col.startswith("INTERN_")
        }
        gdf = gdf.rename(columns=rename_columns)

        # unpack json strings
        for col, deserialization_func in {
            "_VegTypeInfo": VegTypeInfo.deserialize_list,
            "_HabitatKeuze": HabitatKeuze.deserialize_list,
            "_HabitatVoorstel": HabitatVoorstel.deserialize_list2,
        }.items():
            gdf[col] = gdf[col].apply(deserialization_func)

        # check for changed habitatkeuzes
        rename_columns = {
            col: col[len("EDIT_") :] for col in gdf.columns if col.startswith("EDIT_")
        }
        gdf = gdf.rename(columns=rename_columns)
        altered_habkeuzes = gdf.apply(cls._multi_col_to_habkeuze, axis=1)
        for row_idx, (new_keuzes, old_keuzes) in enumerate(
            zip(altered_habkeuzes, gdf["_HabitatKeuze"])
        ):
            if len(new_keuzes) != len(old_keuzes):
                logging.error(
                    "Het aantal complexdelen is veranderd door de gebruiker. Wij kunnen niet garanderen dat de output correct is."
                )
            for new_keuze, old_keuze in zip(new_keuzes, old_keuzes):
                new_habtype, new_kwaliteit = new_keuze
                if (
                    new_habtype != old_keuze.habtype
                    or new_kwaliteit != old_keuze.kwaliteit.as_letter()
                ):
                    logging.warning(
                        f"Er zijn handmatige wijzigingen in de habitattypes. Deze worden overgenomen. In vlak: ElmID={gdf['ElmID'].iloc[row_idx]}"
                    )
                    old_keuze.status = KeuzeStatus.HANDMATIG_TOEGEKEND
                    old_keuze.habtype = new_habtype
                    old_keuze.kwaliteit = Kwaliteit.from_letter(new_kwaliteit)

        gdf = gdf.rename(
            columns={
                "_VegTypeInfo": "VegTypeInfo",
                "_HabitatVoorstel": "HabitatVoorstel",
                "_HabitatKeuze": "HabitatKeuze",
                "LokVrtNar": "_LokVrtNar",
                "LokVegTyp": "_LokVegTyp",
                "state": "_state",
            }
        )
        gdf = gdf.drop(
            columns=gdf.columns[gdf.columns.str.startswith(("Habtype", "Kwal"))]
        )

        gdf["_state"] = gdf["_state"].apply(KarteringState)

        kartering = cls(gdf)
        kartering.check_state(
            KarteringState.MITS_HABKEUZES,
            KarteringState.MOZAIEK_HABKEUZES,
            KarteringState.FUNC_SAMENHANG,
        )

        return kartering

    def as_final_format(self) -> gpd.GeoDataFrame:
        """
        Output de kartering conform het format voor habitattypekarteringen zoals beschreven
        in het Gegevens Leverings Protocol (Bijlage 3a)
        """
        self.check_state(
            KarteringState.MITS_HABKEUZES,
            KarteringState.MOZAIEK_HABKEUZES,
            KarteringState.FUNC_SAMENHANG,
        )

        # Base dataframe conform Gegevens Leverings Protocol maken
        base = self.gdf[
            [
                "Area",
                "Opm",
                "Datum",
                "ElmID",
                "geometry",
                "VegTypeInfo",
                "HabitatKeuze",
                "_LokVegTyp",
                "_LokVrtNar",
                "_state",
            ]
        ]

        final = pd.concat([base, base.apply(self.row_to_final_format, axis=1)], axis=1)
        final["_Samnvttng"] = final.apply(build_aggregate_habtype_field, axis=1)
        final["_state"] = final["_state"].apply(lambda x: x.value)
        final = finalize_final_format(final)

        # arcgis kan geen kolommen beginnend met een _ laten zien, dus zetten we er even wat voor
        fix_arcgis_underscore = {
            col: f"f{col}" for col in final.columns if col.startswith("_")
        }
        final = final.rename(columns=fix_arcgis_underscore)

        return final

    def row_to_final_format(self, row) -> pd.Series:
        """
        Maakt van een rij een dataseries met blokken kolommen volgens het Gegevens Leverings Protocol (Bijlage 3a)
        """
        keuzes = row["HabitatKeuze"]
        vegtypeinfos = row["VegTypeInfo"]

        assert len(keuzes) > 0, "Er zijn vlakken zonder habitatkeuze"

        # We bijna hebben altijd even veel keuzes als vegtypeinfos
        # Want ieder vegtypeinfo leid tot een habitattype (of tot H0000 of tot HXXXX)
        if len(keuzes) != len(vegtypeinfos):
            # Maar als we niet even veel keuzes als vegtypeinfos hebben, dan moet dat zijn
            # omdat dit vlak vanuit de vegetatiekartering geen vegtypen heeft gekregen
            assert (
                len(vegtypeinfos) == 0
            ), "Mismatch tussen aantal habitatkeuzes en vegtypeinfos; vegtypeinfos zijn niet leeg"
            assert (
                len(keuzes) == 1
                and keuzes[0].status == KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN
            ), "Geen opgegeven vegtypen maar status is niet GEEN_OPGEGEVEN_VEGTYPEN"
            # In dit geval geven we een dummy/padding vegtypeinfo mee, dan hoeven we niet nog een extra
            # versie van hab_as_final_format te maken die geen vegtypeinfo nodig heeft
            vegtypeinfos = [
                VegTypeInfo(
                    percentage=0,
                    SBB=[],
                    VvN=[],
                )
            ]

        return pd.concat(
            [
                hab_as_final_format(print_info, i + 1, row["Area"])
                for i, print_info in enumerate(zip(keuzes, vegtypeinfos))
            ]
        )

    def final_format_to_file(self, path: Path) -> None:
        """
        Slaat de kartering op in een shapefile
        """
        final = self.as_final_format()
        path.parent.mkdir(parents=True, exist_ok=True)
        final.to_file(path)

    def get_geometry_mask(self) -> gpd.GeoDataFrame:
        """
        Geeft een gdf met alleen de geometrieen van de kartering,
        bedoeld voor masking bij inladen grote gpkg's, zoals bodemkaart en LBK
        """
        return self.gdf[["geometry"]]

    def __len__(self) -> int:
        return len(self.gdf)
