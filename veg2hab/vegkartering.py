import logging
import warnings
from collections import defaultdict
from dataclasses import dataclass
from numbers import Number
from pathlib import Path
from typing import List, Optional, Union

import geopandas as gpd
import pandas as pd
from typing_extensions import Literal, Self

from veg2hab.acces_db import read_access_tables
from veg2hab.criteria import FGRCriterium, is_criteria_type_present
from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.fgr import FGR
from veg2hab.habitat import (
    HabitatVoorstel,
    rank_habitatkeuzes,
    try_to_determine_habkeuze,
)
from veg2hab.mozaiek import (
    calc_mozaiek_percentages_from_overlay_gdf,
    make_buffered_boundary_overlay_gdf,
)
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import VvN as _VvN


@dataclass
class VegTypeInfo:
    """
    Klasse met alle informatie over één vegetatietype van een vlak
    """

    percentage: Number
    SBB: List[_SBB]
    VvN: List[_VvN]

    def __post_init__(self):
        assert len(self.SBB) <= 1, "Er kan niet meer dan 1 SBB type zijn"
        assert isinstance(
            self.percentage, Number
        ), f"Percentage moet een getal (int/float/double/etc) zijn. Nu is het {self.percentage} {type(self.percentage)}"

    @classmethod
    def from_str_vegtypes(
        cls,
        percentage: Union[None, str, Number],
        VvN_strings: List[Optional[str]] = [],
        SBB_strings: List[Optional[str]] = [],
    ) -> Self:
        """
        Aanmaken vanuit string vegetatietypen
        """
        if isinstance(percentage, str):
            percentage = float(percentage.replace(",", "."))

        assert isinstance(
            percentage, Number
        ), f"Percentage moet een getal zijn, nu is het {percentage} {type(percentage)}"

        assert (
            len(VvN_strings + SBB_strings) > 0
        ), "Er moet minstens 1 vegetatietype zijn"

        vvn = [_VvN.from_string(i) for i in VvN_strings]
        sbb = [_SBB.from_string(i) for i in SBB_strings]

        return cls(
            percentage=percentage,
            VvN=[v for v in vvn if v is not None],
            SBB=[s for s in sbb if s is not None],
        )

    @classmethod
    def create_vegtypen_list_from_access_rows(
        cls,
        rows: pd.DataFrame,
        perc_col: str,
        SBB_col: str,
    ) -> List["VegTypeInfo"]:
        """
        Maakt van alle rijen met vegetatietypes van een vlak
        (via groupby bv) een lijst van VegetatieTypeInfo objecten
        """
        lst = []

        for _, row in rows.iterrows():
            # Als er geen percentage is, willen we ook geen VegTypeInfo,
            if pd.isna(row[perc_col]) or row[perc_col] == 0:
                continue
            # Als er geen vegtypen zijn, willen we ook geen VegTypeInfo,
            if pd.isna(row[SBB_col]):
                continue
            lst.append(
                cls.from_str_vegtypes(
                    row[perc_col],
                    VvN_strings=[],
                    SBB_strings=[row[SBB_col]] if SBB_col else [],
                )
            )
        return lst

    def __str__(self):
        return f"({self.percentage}%, SBB: {[str(x) for x in self.SBB]}, VvN: {[str(x) for x in self.VvN]})"

    def __hash__(self):
        return hash((self.percentage, tuple(self.VvN), tuple(self.SBB)))


def ingest_vegtype(
    gdf: gpd.GeoDataFrame,
    sbb_cols: Optional[List[str]],
    vvn_cols: Optional[List[str]],
    perc_cols: List[str],
) -> pd.Series:
    """
    Leest de vegetatietypen van een vlak in en maakt er een lijst van VegTypeInfo objecten van
    Vlakken zonder percentage
    """
    # Validatie
    if sbb_cols is not None and len(sbb_cols) != len(perc_cols):
        raise ValueError(
            f"De lengte van sbb_cols ({len(sbb_cols)}) moet 0 zijn of gelijk zijn aan de lengte van perc_col ({len(perc_cols)})"
        )

    if vvn_cols is not None and len(vvn_cols) != len(perc_cols):
        raise ValueError(
            f"De lengte van vvn_cols ({len(vvn_cols)}) moet 0 zijn of gelijk zijn aan de lengte van perc_col ({len(perc_cols)})"
        )

    assert sbb_cols or vvn_cols, "Er moet een SBB of VvN kolom zijn"

    # Inlezen
    if not sbb_cols:
        sbb_cols = [None] * len(perc_cols)
    if not vvn_cols:
        vvn_cols = [None] * len(perc_cols)

    def _row_to_vegtypeinfo_list(row: gpd.GeoSeries) -> List[VegTypeInfo]:
        vegtype_list = []
        for sbb_col, vvn_col, perc_col in zip(sbb_cols, vvn_cols, perc_cols):
            # Als er geen percentage is, willen we ook geen VegTypeInfo,
            # dus slaan we deze over
            if pd.isnull(row[perc_col]) or row[perc_col] == 0:
                continue

            # Als er geen vegtypen zijn, willen we ook geen VegTypeInfo,
            # dus slaan we deze over
            if (pd.isnull(row[sbb_col]) if sbb_col else True) and (
                pd.isnull(row[vvn_col]) if vvn_col else True
            ):
                continue

            vegtypeinfo = VegTypeInfo.from_str_vegtypes(
                row[perc_col],
                VvN_strings=[row[vvn_col]] if vvn_col else [],
                SBB_strings=[row[sbb_col]] if sbb_col else [],
            )

            vegtype_list.append(vegtypeinfo)
        return vegtype_list

    return gdf.apply(_row_to_vegtypeinfo_list, axis=1)


def fill_in_percentages(
    row: gpd.GeoSeries,
    vegtype_col_format: Literal["single", "multi"],
    perc_col: Union[str, List[str]],
    sbb_col: Union[str, List[str], None] = None,
    vvn_col: Union[str, List[str], None] = None,
) -> gpd.GeoSeries:
    """
    Vult percentages in voor een rij. Ieder vegetatietype krijgt een percentage van 100/n_vegtypen.
    """
    assert (
        vvn_col is not None or sbb_col is not None
    ), "Er moet een SBB of VvN kolom zijn"

    assert vegtype_col_format == "multi"

    # Uitzoeken hoeveel vegtypen er zijn
    vvn_present = row[vvn_col].notna().reset_index(drop=True) if vvn_col else False
    sbb_present = row[sbb_col].notna().reset_index(drop=True) if sbb_col else False
    vegtype_present = vvn_present | sbb_present
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


def sorteer_vegtypeinfos_habvoorstellen(row: gpd.GeoSeries) -> gpd.GeoSeries:
    """
    Habitatkeuzes horen op een vaste volgorde: Eerst alle niet-H0000, dan op percentage, dan op kwaliteit
    Deze method ordent de Habitatkeuzes en zorgt ervoor dat de bij elke keuze horende VegTypeInfos ook op de juiste volgorde worden gezet
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

    keuze_en_vegtypeinfo = list(zip(row["HabitatKeuze"], row["VegTypeInfo"]))
    # Sorteer op basis van de habitatkeuze (idx 0)
    sorted_keuze_en_vegtypeinfo = sorted(keuze_en_vegtypeinfo, key=rank_habitatkeuzes)

    row["HabitatKeuze"], row["VegTypeInfo"] = zip(*sorted_keuze_en_vegtypeinfo)
    # Tuples uit zip omzetten naar lists
    row["HabitatKeuze"], row["VegTypeInfo"] = list(row["HabitatKeuze"]), list(
        row["VegTypeInfo"]
    )
    return row


def mozaiekregel_habtype_percentage_dict_to_string(
    habtype_percentage_dict: Union[None, dict]
) -> str:
    """
    Maakt een mooie output-ready string van een habtype_percentage_dict voor mozaiekregels
    Dict heeft als keys (habtype (str), zelfstandig (bool), kwaliteit (Kwaliteit))

    Van:
    {
        ("H1234", True, Kwaliteit.GOED): 70.0,
        ("H5678", False, Kwaliteit.MATIG): 20.0,
        ("HXXXX", True, Kwaliteit.NVT): 10.0
    }

    Naar:
    "70.00% goed zelfstandig H1234, 20.00% matig mozaiek H5678, 10.00% zelfstandig HXXXX"

    """
    # Als er nergens mozaiekregels zijn, is er ook geen dict
    if habtype_percentage_dict is None:
        return ""

    return ", ".join(
        f"{v:.2f}% {'goed ' if k[2] == Kwaliteit.GOED else 'matig ' if k[2] == Kwaliteit.MATIG else ''}{'zelfstandig' if k[1] else 'mozaiek'} {k[0]}"
        for k, v in habtype_percentage_dict.items()
        if v > 0
    )


def hab_as_final_format(print_info: tuple, idx: int, opp: float) -> pd.Series:
    """ """

    keuze, vegtypeinfo = print_info

    # Er is 1 HabitatVoorstel
    if len(keuze.habitatvoorstellen) == 1:
        if keuze.status in [
            KeuzeStatus.DUIDELIJK,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
            KeuzeStatus.PLACEHOLDER,
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
        ]:
            voorstel = keuze.habitatvoorstellen[0]
            series_dict = {
                f"Habtype{idx}": keuze.habtype,
                f"Perc{idx}": vegtypeinfo.percentage,
                f"Opp{idx}": opp * vegtypeinfo.percentage,
                f"Kwal{idx}": keuze.kwaliteit.as_letter(),
                f"Opm{idx}": keuze.opmerking,
                f"Mits_opm{idx}": keuze.mits_opmerking,
                f"Mozk_opm{idx}": keuze.mozaiek_opmerking,
                f"MozkDict{idx}": mozaiekregel_habtype_percentage_dict_to_string(
                    keuze.habitatvoorstellen[0].mozaiek_dict
                ),
                # f"Bron{idx}" TODO: Naam van de kartering, voegen we later toe
                f"VvN{idx}": (
                    str(voorstel.onderbouwend_vegtype)
                    if isinstance(voorstel.onderbouwend_vegtype, _VvN)
                    else None
                ),
                f"SBB{idx}": (
                    str(voorstel.onderbouwend_vegtype)
                    if isinstance(voorstel.onderbouwend_vegtype, _SBB)
                    else None
                ),
                # f"VEGlok{idx}" TODO: Doen we voor nu nog even niet
                f"_Status{idx}": str(keuze.status),
                f"_Uitleg{idx}": keuze.status.toelichting(),
                f"_VvNdftbl{idx}": (
                    str([str(voorstel.vegtype_in_dt), voorstel.idx_in_dt])
                    if isinstance(voorstel.vegtype_in_dt, _VvN)
                    else None
                ),
                f"_SBBdftbl{idx}": (
                    str([str(voorstel.vegtype_in_dt), voorstel.idx_in_dt])
                    if isinstance(voorstel.vegtype_in_dt, _SBB)
                    else None
                ),
                # Als de status GEEN_OPGEGEVEN_VEGTYPEN is, dan willen we bij VgTypInf niks invullen
                f"_VgTypInf{idx}": (
                    str(vegtypeinfo)
                    if keuze.status != KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN
                    else None
                ),
                f"_ChkNodig{idx}": (
                    True
                    if keuze.status
                    in [
                        KeuzeStatus.PLACEHOLDER,
                        KeuzeStatus.WACHTEN_OP_MOZAIEK,
                    ]
                    else False
                ),
            }

            return pd.Series(series_dict)

        assert (
            False
        ), f"Er is 1 habitatkeuze maar KeuzeStatus {keuze.status} is niet DUIDELIJK, VEGTYPEN_NIET_IN_DEFTABEL of GEEN_KLOPPENDE_MITSEN"

    if keuze.status in [
        KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
        KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        KeuzeStatus.PLACEHOLDER,
        KeuzeStatus.WACHTEN_OP_MOZAIEK,
    ]:
        voorstellen = keuze.habitatvoorstellen
        # Als alle voorgestelde habtypen hetzelfde zijn kunnen we ze plat slaan
        # NOTE: Wordt keuzestatus dan ook weer duidelijk? Moet deze check dan al in habitatkeuze_obv_mitsen gedaan worden?
        voorgestelde_hab_en_kwal = [
            [voorstel.habtype, voorstel.kwaliteit] for voorstel in voorstellen
        ]
        if all(hab == voorgestelde_hab_en_kwal[0] for hab in voorgestelde_hab_en_kwal):
            voorgestelde_hab_en_kwal = [voorgestelde_hab_en_kwal[0]]
        series_dict = {
            f"Habtype{idx}": keuze.habtype,
            f"Perc{idx}": str(vegtypeinfo.percentage),
            f"Opp{idx}": str(opp * vegtypeinfo.percentage),
            f"Kwal{idx}": keuze.kwaliteit.as_letter(),
            f"Opm{idx}": keuze.opmerking,
            f"Mits_opm{idx}": keuze.mits_opmerking,
            f"Mozk_opm{idx}": keuze.mozaiek_opmerking,
            f"MozkDict{idx}": mozaiekregel_habtype_percentage_dict_to_string(
                keuze.habitatvoorstellen[0].mozaiek_dict
            ),
            # f"Bron{idx}" TODO: Naam van de kartering, voegen we later toe
            f"VvN{idx}": str(
                [
                    (
                        str(voorstel.onderbouwend_vegtype)
                        if isinstance(voorstel.onderbouwend_vegtype, _VvN)
                        else None
                    )
                    for voorstel in voorstellen
                ]
            ),
            f"SBB{idx}": str(
                [
                    (
                        str(voorstel.onderbouwend_vegtype)
                        if isinstance(voorstel.onderbouwend_vegtype, _SBB)
                        else None
                    )
                    for voorstel in voorstellen
                ]
            ),
            # f"VEGlok{idx}" TODO: Doen we voor nu nog even niet
            f"_Status{idx}": str(keuze.status),
            f"_Uitleg{idx}": keuze.status.toelichting(),
            f"_VvNdftbl{idx}": str(
                [
                    (
                        str([str(voorstel.vegtype_in_dt), voorstel.idx_in_dt])
                        if isinstance(voorstel.vegtype_in_dt, _VvN)
                        else None
                    )
                    for voorstel in voorstellen
                ]
            ),
            f"_SBBdftbl{idx}": str(
                [
                    (
                        str([str(voorstel.vegtype_in_dt), voorstel.idx_in_dt])
                        if isinstance(voorstel.vegtype_in_dt, _SBB)
                        else None
                    )
                    for voorstel in voorstellen
                ]
            ),
            f"_VgTypInf{idx}": str(vegtypeinfo),
            f"_ChkNodig{idx}": (
                True
                if keuze.status
                in [
                    KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
                    KeuzeStatus.PLACEHOLDER,
                    KeuzeStatus.WACHTEN_OP_MOZAIEK,
                ]
                else False
            ),
        }

        return pd.Series(series_dict)

    assert (
        False
    ), f"hab_as_final_form voor KeuzeStatus {keuze.status} is niet geimplementeerd"


def bepaal_ChckNodig(row: gpd.GeoSeries) -> bool:
    """
    Bepaalt of een rij een habitattypekartering een handmatige controle nodig heeft
    """
    check_nodigs = [col for col in row.index if "_ChkNodig" in col]
    if any(row[check_nodig] == True for check_nodig in check_nodigs):
        return True
    return False


def build_aggregate_habtype_field(row: gpd.GeoSeries) -> str:
    """
    Maakt een samenvattende string van de habitattypen van een rij
    Hierbij worden de percentages van alle habtype/kwaliteit tuples bij elkaar
    Voorbeeld: 70% H1234 (G), 20% H0000, 10% HXXXX
    """
    habitatkeuzes = row["HabitatKeuze"]
    vegtypeinfos = row["VegTypeInfo"]

    assert len(habitatkeuzes) > 0, "Er moet minstens 1 habitatkeuze zijn"

    # Hierin krijgen we per (habtype, kwaliteit) tuple de som van de percentages
    aggregate = defaultdict(float)

    # Als het vlak geen opgegeven habitattype heeft, heeft het geen vegtype infos,
    # dus heeft het ook geen opgegeven percentage, dus moeten we die handmatig op 100 zetten
    if habitatkeuzes[0].status == KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN:
        assert (
            len(habitatkeuzes) == 1
        ), "Bij KeuzeStatus GEEN_OPGEGEVEN_VEGTYPE mag er maar 1 habitatkeuze zijn"
        assert (
            vegtypeinfos == []
        ), "Bij KeuzeStatus GEEN_OPGEGEVEN_VEGTYPE mag er geen VegTypeInfo zijn"
        aggregate[
            (habitatkeuzes[0].habtype, habitatkeuzes[0].kwaliteit.as_letter())
        ] = 100
    else:
        # In alle andere gevallen kunnen we gewoon de percentages bij de habitatkeuze
        # horende VegTypeInfos gebuiken
        for keuze, info in zip(habitatkeuzes, vegtypeinfos):
            aggregate[(keuze.habtype, keuze.kwaliteit.as_letter())] += info.percentage

    # Sorteren op (percentage, habtype, kwaliteit) zodat de string
    # altijd hetzelfde is bij dezelfde habtype/kwaliteit/percentage permutaties
    aggregate = dict(
        sorted(aggregate.items(), key=(lambda item: (-item[1], item[0][0], item[0][1])))
    )

    # Maken van alle losse strings
    aggregate_strings = []
    for key, value in aggregate.items():
        aggregate_string = f"{float(value)}% {key[0]}"
        if key[1] in [
            Kwaliteit.GOED,
            Kwaliteit.MATIG,
        ]:
            aggregate_string += f" ({key[1]})"
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
        "_ChkNodig",
        "_Samnvttng",
        "_LokVrtNar",
    ]
    n_habtype_blocks = len([i for i in gdf.columns if "Habtype" in i])
    for i in range(1, n_habtype_blocks + 1):
        new_columns = new_columns + [
            f"Habtype{i}",
            f"Perc{i}",
            f"Opp{i}",
            f"Kwal{i}",
            f"Opm{i}",
            f"Mits_opm{i}",
            f"Mozk_opm{i}",
            f"MozkDict{i}",
            f"VvN{i}",
            f"SBB{i}",
            f"_Status{i}",
            f"_Uitleg{i}",
            f"_VvNdftbl{i}",
            f"_SBBdftbl{i}",
            f"_VgTypInf{i}",
            f"_ChkNodig{i}",
        ]
    return gdf[new_columns]


def fix_crs(
    gdf: gpd.GeoDataFrame, shape_path: Path = "onbekende locatie"
) -> gpd.GeoDataFrame:
    """
    Geeft voor gdfs zonder crs een warning en zet ze om naar EPSG:28992
    Zet gdfs met een andere crs dan EPSG:28992 om naar EPSG:28992
    """
    if gdf.crs is None:
        logging.warn(f"CRS van {shape_path} was None en is nu gelezen als EPSG:28992")
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
    split_char: Optional[str] = None,
    perc_col: Optional[str] = None,
) -> gpd.GeoDataFrame:
    """
    Converteert een "single" kolomformat dataframe naar een "multi" kolomformat dataframe
    De nieuwe "multi" format kolommen heten SBB1/2/3/..., VvN1/2/3/... en perc1/2/3/...
    """
    # Uitvinden hoe veel kolommen er moeten komen
    assert SBB_col or VvN_col, "Er moet een SBB of VvN kolom zijn"
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

    for col in [SBB_col, VvN_col, perc_col]:
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
        SBB_col = [f"{SBB_col}{idx+1}" for idx in range(n_cols_needed)]
        # Stel dat er max 3 VvN zijn en max 2 SBB, dan moet de SBB3 nog wel bestaan
        for col in SBB_col:
            if col not in gdf.columns:
                gdf[col] = None

    if VvN_col:
        VvN_col = [f"{VvN_col}{idx+1}" for idx in range(n_cols_needed)]
        for col in VvN_col:
            if col not in gdf.columns:
                gdf[col] = None

    if perc_col:
        perc_col = [f"{perc_col}{idx+1}" for idx in range(n_cols_needed)]
        for col in perc_col:
            if col not in gdf.columns:
                gdf[col] = None

    return gdf, SBB_col, VvN_col, perc_col


class Kartering:
    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Alle VegTypeInfo sorteren op percentage van hoog naar laag
        # (Dit voornamelijk omdat dan als bij de mozaiekregels v0.1 we overal de eerste habitatkeuze
        #  als enige habitatkeuze nemen, we altijd de habitatkeuze met het hoogste percentage nemen)
        self.gdf["VegTypeInfo"] = self.gdf["VegTypeInfo"].apply(
            lambda x: sorted(x, key=lambda y: y.percentage, reverse=True)
        )

        # NOTE: evt iets van self.stage = lokaal/sbb/vvn ofzo? Enum?
        #       Misschien een dict met welke stappen gedaan zijn?

    @classmethod
    def from_access_db(
        cls,
        shape_path: Path,
        shape_elm_id_column: str,
        access_mdb_path: Path,
        opmerkingen_column: Optional[str] = "Opmerking",
        datum_column: Optional[str] = "Datum",
    ) -> Self:
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile en
        een access database die al is opgedeeld in losse csv bestanden.

        # .shp shp_elm_id_column -> ElmID in Element.csv voor intern_id -> Locatie in KarteringVegetatietype.csv voor Vegetatietype ->
        #      -> Code in Vegetatietype.csv voor SbbType -> Cata_ID in SsbType.csv voor Code (hernoemd naar Sbb)
        """
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
            if col in gdf.columns
        ]
        gdf = gdf[columns_to_keep]

        # Als kolommen niet aanwezig zijn in de shapefile dan vullen we ze met None
        for col in [opmerkingen_column, datum_column]:
            if col not in gdf.columns:
                gdf[col] = None

        # Standardiseren van kolomnamen
        gdf = gdf.rename(
            columns={opmerkingen_column: "Opmerking", datum_column: "Datum"}
        )
        gdf["Opp"] = gdf["geometry"].area
        gdf["_LokVrtNar"] = "Lokale typologie is primair vertaald naar SBB"

        element, grouped_kart_veg = read_access_tables(access_mdb_path)

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

        # Joinen van de SBBs aan de gdf
        gdf = gdf.merge(
            grouped_kart_veg, left_on="intern_id", right_on="Locatie", how="left"
        )

        # We laten alle NA vegtype-informatie vallen - dit kan komen door geometry die lijnen zijn in plaats van vormen,
        # maar ook aan ontbrekende waarden in een van de csv-bestanden.
        if gdf.VegTypeInfo.isnull().any():
            logging.warn(
                f"Er zijn {gdf.VegTypeInfo.isnull().sum()} vlakken zonder VegTypeInfo in {shape_path}. Deze worden verwijderd."
            )
            logging.warn(
                f"De eerste paar ElmID van de verwijderde vlakken zijn: {gdf[gdf.VegTypeInfo.isnull()].ElmID.head().to_list()}"
            )
            gdf = gdf.dropna(subset=["VegTypeInfo"])

        return cls(gdf)

    @classmethod
    def from_shapefile(
        cls,
        shape_path: Path,
        ElmID_col: str,
        vegtype_col_format: Literal["single", "multi"],
        sbb_of_vvn: Literal["VvN", "SBB", "beide"],
        datum_col: Optional[str] = None,
        opmerking_col: Optional[str] = None,
        SBB_col: Optional[str] = None,
        VvN_col: Optional[str] = None,
        split_char: Optional[str] = "+",
        perc_col: Optional[str] = None,
    ) -> Self:
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile.
        Input:
        - shape_path: het pad naar de shapefile
        - ElmID_col: de kolomnaam van de ElementID in de Shapefile; uniek per vlak
        - vegtype_col_format: "single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn
        - sbb_of_vvn: "VvN" als VvN de voorname vertaling is vanuit het lokale type, "SBB" voor SBB en "beide" als beide er zijn.
        - datum_col: kolomnaam van de datum als deze er is
        - opmerking_col: kolomnaam van de opmerking als deze er is
        - VvN_col: kolomnaam van de VvN vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char)
        - SBB_col: kolomnaam van de SBB vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char)
        - split_char: karakter waarop de vegetatietypen gesplitst moeten worden (voor complexen (bv "16aa2+15aa")) (wordt bij mutli_col gebruikt om de kolommen te scheiden)
        - percentage_col: kolomnaam van de percentage als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char))
        """

        ###############
        ##### Valideren, opschonen en aanvullen van de shapefile
        ###############

        shapefile = gpd.read_file(shape_path)

        if ElmID_col and not shapefile[ElmID_col].is_unique:
            # NOTE: Als we ElmID nooit door hoeven te voeren tot in de habitattypekartering kan deze ook helemaal
            #       uit de spreadsheets gehaald worden; dan gebruiken we gewoon altijd onze eigen.
            warnings.warn(
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

        # Selectie van de te bewaren kolommen
        cols = [
            col for col in [datum_col, opmerking_col] if col in shapefile.columns
        ] + [ElmID_col, "geometry"]
        # Uitvinden welke vegtype kolommen er mee moeten
        if vegtype_col_format == "multi":
            if SBB_col is not None:
                SBB_col = SBB_col.split(split_char)
                cols += SBB_col
            if VvN_col is not None:
                VvN_col = VvN_col.split(split_char)
                cols += VvN_col
            if perc_col is not None:
                perc_col = perc_col.split(split_char)
                cols += perc_col
        else:
            cols += [col for col in [VvN_col, SBB_col, perc_col] if col is not None]
        if not all(col in shapefile.columns for col in cols):
            raise ValueError(
                f"Niet alle opgegeven kolommen ({cols}) gevonden in de shapefile kolommen ({shapefile.columns})"
            )
        gdf = shapefile[cols].copy()

        # Standardiseren van kolomnamen
        gdf = gdf.rename(
            columns={ElmID_col: "ElmID", opmerking_col: "Opmerking", datum_col: "Datum"}
        )
        ElmID_col = "ElmID"
        opmerking_col = "Opmerking"
        datum_col = "Datum"

        gdf = fix_crs(gdf, shape_path)

        if vegtype_col_format == "single":
            gdf, SBB_col, VvN_col, perc_col = _single_to_multi(
                gdf=gdf,
                SBB_col=SBB_col,
                VvN_col=VvN_col,
                split_char=split_char,
                perc_col=perc_col,
            )
            vegtype_col_format = "multi"

        # Opschonen
        if SBB_col:
            gdf[SBB_col] = gdf[SBB_col].apply(_SBB.opschonen_series)

        if VvN_col:
            gdf[VvN_col] = gdf[VvN_col].apply(_VvN.opschonen_series)

        # Als er geen datum of opmerking kolom is, dan maken we die en vullen we deze met None
        datum_col = "Datum" if datum_col is None else datum_col
        opmerking_col = "Opmerking" if opmerking_col is None else opmerking_col
        for col in [datum_col, opmerking_col]:
            if col not in gdf.columns:
                gdf[col] = None

        # Standardiseren van kolomnamen
        gdf = gdf.rename(columns={datum_col: "Datum", opmerking_col: "Opmerking"})
        gdf["Opp"] = gdf["geometry"].area
        LokVrtNar_string = sbb_of_vvn if sbb_of_vvn != "beide" else "zowel SBB als VvN"
        gdf[
            "_LokVrtNar"
        ] = f"Lokale typologie is primair vertaald naar {LokVrtNar_string}"

        # Percentages invullen als die er niet zijn
        if perc_col is None:
            if vegtype_col_format == "multi":
                perc_col = [
                    f"perc_{n}"
                    for n in range(
                        max([len(col) for col in [SBB_col, VvN_col] if col is not None])
                    )
                ]
            else:
                perc_col = "perc"
            gdf = gdf.apply(
                lambda row: fill_in_percentages(
                    row, vegtype_col_format, perc_col, SBB_col, VvN_col
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
            perc_col,
        )

        return cls(gdf)

    def apply_wwl(
        self, wwl: "WasWordtLijst", override_existing_VvN: bool = False
    ) -> None:
        """
        Past de was-wordt lijst toe op de kartering om VvN toe te voegen aan SBB-only karteringen
        """
        assert "VegTypeInfo" in self.gdf.columns, "Er is geen kolom met VegTypeInfo"

        # Check dat er niet al VvN aanwezig zijn in de VegTypeInfo's
        # NOTE: Als dit te langzaam blijkt is een steekproef wss ook voldoende
        # NOTE NOTE: Als we zowel SBB en VvN uit de kartering hebben, willen we
        #            dan nog wwl doen voor de SBB zonder al meegegeven VvN?
        VvN_already_present = self.gdf["VegTypeInfo"].apply(
            lambda infos: any(len(info.VvN) > 0 for info in infos)
        )
        if VvN_already_present.any() and not override_existing_VvN:
            warnings.warn(
                "Er zijn al VvN aanwezig in de kartering. De was-wordt lijst wordt niet toegepast."
            )
            return

        self.gdf["VegTypeInfo"] = self.gdf["VegTypeInfo"].apply(
            wwl.toevoegen_VvN_aan_List_VegTypeInfo
        )

    def apply_deftabel(self, dt: "DefinitieTabel") -> None:
        """
        Past de definitietabel toe op de kartering om habitatvoorstellen toe te voegen
        """
        assert "VegTypeInfo" in self.gdf.columns, "Er is geen kolom met VegTypeInfo"
        # NOTE: Hier iets wat vast stelt dat er tenminste 1 VegTypeInfo met een VvN is, zo niet geef warning? (want dan is wwl wss niet gedaan)
        #       - klinkt wel logisch maar het is ook mogelijk dat geen van de SBB een VvN in de wwl hebben
        #         dus dan is een warning geveb en niet de deftabel toepassen ook niet handig
        # @ reviewer, goeie andere opties?

        self.gdf["HabitatVoorstel"] = self.gdf["VegTypeInfo"].apply(
            lambda infos: [dt.find_habtypes(info) for info in infos]
            if len(infos) > 0
            else [[HabitatVoorstel.H0000_no_vegtype_present()]]
        )

    def check_mitsen(self, fgr: FGR) -> None:
        """
        Checkt of de mitsen in de habitatvoorstellen van de kartering wordt voldaan.
        """
        assert (
            "HabitatVoorstel" in self.gdf.columns
        ), "Er is geen kolom met HabitatVoorstel"

        # Deze dataframe wordt verrijkt met de info nodig om mitsen te checken.
        mits_info_df = gpd.GeoDataFrame(self.gdf.geometry)

        ### Bepaal waar meer informatie nodig is
        # FGR
        fgr_needed = self.gdf["HabitatVoorstel"].apply(
            is_criteria_type_present, args=(FGRCriterium,)
        )
        # Bodem
        # etc

        ### Verrijken met de benodigde informatie
        # FGR
        mits_info_df["fgr"] = fgr.fgr_for_geometry(mits_info_df.loc[fgr_needed]).drop(
            columns="index_right"
        )
        # Bodem
        # etc

        ### Mitsen checken
        for idx, row in self.gdf.iterrows():
            mits_info_row = mits_info_df.loc[idx]
            for voorstellen in row.HabitatVoorstel:
                for voorstel in voorstellen:
                    if voorstel.mits is None:
                        raise ValueError("Er is een habitatvoorstel zonder mits")
                    voorstel.mits.check(mits_info_row)

        # NOTE: Kan weg zo als dit in bepaal_habtitatkeuzes gebeurt
        # ### Habitatkeuzes bepalen
        # self.gdf["HabitatKeuze"] = self.gdf["HabitatVoorstel"].apply(
        #     lambda voorstellen: [
        #         habitatkeuze_obv_mitsen(voorstel) for voorstel in voorstellen
        #     ]
        # )

    def bepaal_habitatkeuzes(self, fgr: FGR, max_iter: int = 20) -> None:
        """ """
        # We starten alle HabitatKeuzes op None, en dan vullen we ze steeds verder in
        self.gdf["HabitatKeuze"] = self.gdf.VegTypeInfo.apply(
            lambda voorstellen_list: [None for sublist in voorstellen_list]
        )
        self.gdf["finished_on_iteration"] = 0

        ### Checken mitsen
        self.check_mitsen(fgr)

        ### Verkrijgen overlay gdf
        # Hier staat in welke vlakken er voor hoeveel procent aan welke andere vlakken grenzen
        # Als er geen vlakken met mozaiekregels zijn of als deze vlakken allemaal nergens aan grenzen is overlayed None
        overlayed = make_buffered_boundary_overlay_gdf(self.gdf)

        for i in range(max_iter):
            keuzes_still_to_determine_pre = self.gdf.HabitatKeuze.apply(
                lambda keuzes: keuzes.count(None)
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

                # obtain a series with 1 if there is at least 1 None habitatkeuze and 0 otherwise
                finished_on_iteration_increment = self.gdf.HabitatKeuze.apply(
                    lambda keuzes: 1 if keuzes.count(None) > 0 else 0
                )
                self.gdf["finished_on_iteration"] += finished_on_iteration_increment

                # Mergen HabitatVoorstel met overlayed
                # Nu hebben we dus per mozaiekregelvlak voor hoeveel procent het aan welke HabitatKeuzes grenst
                augmented_overlayed = overlayed.merge(
                    self.gdf[["ElmID", "HabitatKeuze"]],
                    on="ElmID",
                    how="left",
                )

                # Deze info zetten we per ElmID om in een defaultdict
                habtype_percentages = calc_mozaiek_percentages_from_overlay_gdf(
                    augmented_overlayed
                )

                # Met deze dicts kunnen we dan de mozaiekregels checken
                self.check_mozaiekregels(habtype_percentages)

            #####
            # Habitatkeuze proberen te bepalen per list habitatvoorstellen van een vegtypeingo
            #####
            self.gdf["HabitatKeuze"] = self.gdf.HabitatVoorstel.apply(
                lambda voorstellen: [
                    try_to_determine_habkeuze(voorstel) for voorstel in voorstellen
                ]
            )

            n_keuzes_still_to_determine_post = self.gdf.HabitatKeuze.apply(
                lambda keuzes: keuzes.count(None)
            ).sum()

            print(
                f"Iteratie {i}: van {n_keuzes_still_to_determine_pre} naar {n_keuzes_still_to_determine_post} keuzes nog te bepalen"
            )

            if (
                n_keuzes_still_to_determine_pre == n_keuzes_still_to_determine_post
                or n_keuzes_still_to_determine_post == 0
            ):
                break
        else:
            warnings.warn(
                f"Maximaal aantal iteraties ({max_iter}) bereikt voor het bepalen van de habitatkeuzes."
            )

        # Of we hebben overal een keuze, of we komen niet verder met nog meer iteraties,
        # of we hebben max_iter bereikt

        if n_keuzes_still_to_determine_post > 0:
            warnings.warn(
                f"Er zijn nog {n_keuzes_still_to_determine_post} habitatkeuzes die niet bepaald konden worden."
            )

    def check_mozaiekregels(self, habtype_percentages):
        for row in self.gdf.itertuples():
            for idx, voorstel_list in enumerate(row.HabitatVoorstel):
                # Als er geen habitatkeuzes zijn (want geen vegtypen opgegeven),
                # dan hoeven we ook geen mozaiekregels te checken
                if len(row.HabitatKeuze) == 0:
                    continue

                # Als we voor deze voorstellen al een HabitatKeuze hebben hoeven we niet weer
                # de mozaiekregels te checken
                if row.HabitatKeuze[idx] is not None:
                    continue

                percentages_dict = habtype_percentages[
                    habtype_percentages["ElmID"] == row.ElmID
                ].dict

                if len(percentages_dict) == 1:
                    percentages_dict = percentages_dict.iloc[0]
                elif len(percentages_dict) == 0:
                    # Vlakken die niet tegen andere vlakken aan liggen zijn er in make_buffered_boundary_overlay_gdf
                    # uitgefilterd door het droppen van lijnen die niet over een vlak liggen.
                    # Deze moeten dus nog even een (lege) dict krijgen

                    # Het kan ook dat dit vlak geen mozaiek nodig heeft (en dus een geenmozaiekregel heeft)
                    percentages_dict = defaultdict(int)
                else:
                    assert (
                        False
                    ), "Er zijn meerdere rijen met hetzelfde ElmID in de habtype_percentages gdf"

                for voorstel in voorstel_list:
                    voorstel.mozaiek.check(percentages_dict)

                    # We bewaren de dict voor bij de output
                    voorstel.mozaiek_dict = percentages_dict

    def as_final_format(self) -> pd.DataFrame:
        """
        Output de kartering conform het format voor habitattypekarteringen zoals beschreven
        in het Gegevens Leverings Protocol (Bijlage 3a)
        """
        assert (
            "HabitatKeuze" in self.gdf.columns
        ), "Er is geen kolom met definitieve habitatvoorstellen"

        # Base dataframe conform Gegevens Leverings Protocol maken
        base = self.gdf[
            [
                "Opp",
                "Opmerking",
                "Datum",
                "ElmID",
                "geometry",
                "VegTypeInfo",
                "HabitatKeuze",
                "_LokVrtNar",
            ]
        ].copy()

        # Sorteer de keuzes eerst op niet-H0000-zijn, dan op percentage, dan op kwaliteit
        base = base.apply(sorteer_vegtypeinfos_habvoorstellen, axis=1)

        base = base.rename(columns={"Opp": "Area", "Opmerking": "Opm"})

        final = pd.concat([base, base.apply(self.row_to_final_format, axis=1)], axis=1)
        final["_ChkNodig"] = final.apply(bepaal_ChckNodig, axis=1)
        final["_Samnvttng"] = final.apply(build_aggregate_habtype_field, axis=1)
        final = finalize_final_format(final)
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
                vegtypeinfos == []
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

    def __len__(self):
        return len(self.gdf)
