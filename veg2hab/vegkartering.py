import warnings
from dataclasses import dataclass
from numbers import Number
from pathlib import Path
from typing import List, Optional, Union

import geopandas as gpd
import pandas as pd
from typing_extensions import Literal

from veg2hab.criteria import FGRCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.fgr import FGR
from veg2hab.habitat import (
    habitatkeuze_obv_mitsen,
    is_criteria_type_present,
    rank_habitatkeuzes,
)
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import VvN as _VvN


@dataclass
class VegTypeInfo:
    """
    Klasse met alle informatie over één vegetatietype van een vlak
    """

    percentage: int
    SBB: List[_SBB]
    VvN: List[_VvN]

    def __post_init__(self):
        assert len(self.SBB) <= 1, "Er kan niet meer dan 1 SBB type zijn"
        assert (
            isinstance(self.percentage, Number) or self.percentage is None
        ), f"Percentage moet een getal (int/float/double/etc) of None zijn. Nu is het {self.percentage} {type(self.percentage)}"

    @classmethod
    def from_str_vegtypes(
        cls,
        percentage: Union[Number, None],
        VvN_strings: List[str] = [],
        SBB_strings: List[str] = [],
    ) -> "VegTypeInfo":
        """
        Aanmaken vanuit string vegetatietypen
        """
        if pd.isna(percentage):
            percentage = 0
        else:
            percentage = float(percentage)

        return cls(
            percentage=percentage,
            VvN=[_VvN.from_string(i) for i in VvN_strings],
            SBB=[_SBB.from_string(i) for i in SBB_strings],
        )

    @classmethod
    def create_vegtypen_list_from_rows(
        cls,
        rows: pd.DataFrame,
        perc_col: str,
        SBB_col: Optional[str] = None,
        VvN_col: Optional[str] = None,
    ) -> List["VegTypeInfo"]:
        """
        Maakt van alle rijen met vegetatietypes van een vlak
        (via groupby bv) een lijst van VegetatieTypeInfo objecten
        """
        assert (
            SBB_col or VvN_col and not (SBB_col and VvN_col)
        ), f"Er moet een SBB of VvN kolom zijn, maar niet beide. Nu is SBB_col={SBB_col} en VvN_col={VvN_col}"
        vegtype_col = VvN_col if VvN_col else SBB_col
        lst = []

        for _, row in rows.iterrows():
            lst.append(
                cls.from_str_vegtypes(
                    row[perc_col],
                    VvN_strings=[row[VvN_col]] if VvN_col else [],
                    SBB_strings=[row[SBB_col]] if SBB_col else [],
                )
            )
        return lst

    def __str__(self):
        return f"({self.percentage}%, SBB: {[str(x) for x in self.SBB]}, VvN: {[str(x) for x in self.VvN]})"

    def __hash__(self):
        return hash((self.percentage, tuple(self.VvN), tuple(self.SBB)))


class Geometrie:
    """Een shape/rij uit de vegetatiekartering.
    Deze bevat of een VvN of een SBB code en een geometrie.
    """

    data: gpd.GeoSeries  # (pandas series?)

    def __init__(self, data: gpd.GeoSeries):
        self.data = data


def ingest_vegtype(
    gdf: gpd.GeoDataFrame,
    ElmID_col: str,
    sbb_cols: Optional[List[str]],
    vvn_cols: Optional[List[str]],
    perc_cols: List[str],
) -> pd.Series:   
    """
    tekst
    """
    # Validatie
    if sbb_cols is not None and len(sbb_cols) != len(perc_cols):
        raise ValueError(
            f"De lengte van sbb_cols ({len(sbb_cols)}) moet gelijk zijn aan de lengte van perc_col ({len(perc_cols)})"
        )

    if vvn_cols is not None and len(vvn_cols) != len(perc_cols):
        raise ValueError(
            f"De lengte van vvn_cols ({len(vvn_cols)}) moet gelijk zijn aan de lengte van perc_col ({len(perc_cols)})"
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
            vegtypeinfo = VegTypeInfo.from_str_vegtypes(
                row[perc_col],
                VvN_strings=[row[vvn_col]] if vvn_col else [],
                SBB_strings=[row[sbb_col]] if sbb_col else [],
            )
            vegtype_list.append(vegtypeinfo)
        return vegtype_list

    return gdf.apply(_row_to_vegtypeinfo_list, axis=1)
    

def ingest_vegtype_column(
    gdf: gpd.GeoDataFrame,
    ElmID_col: str,
    vegtype_col_format: Literal["single", "multi"],
    vegtype_col: Union[str, List[str]],
    vegtype_cls: Union[_SBB, _VvN],
    perc_col: Union[str, List[str]],
    split_char: Optional[str] = None,
) -> pd.Series:
    """
    Leest een kolom met vegetatietypen in en maakt hier VegTypeInfo objecten van
    De kolom wordt eerst gesplitst op een opgegeven karakter (voor complexen (bv "16aa2+15aa")))
    Hierna wordt de kolom geexplode, worden er VegTypeInfo gemaakt van alle vegtypen en deze worden weer op ElmID samengevoegd
    """
    assert (vegtype_col_format == "single") == (
        isinstance(vegtype_col, str)
    ), "Als vegtype_col_format 'single' is, moet vegtype_col een string zijn"

    gdf = gdf.copy()  # Anders krijgen we een SettingWithCopyWarning

    if vegtype_col_format == "multi":
        subset_vegtypen = gdf[vegtype_col + [ElmID_col]].copy()
        subset_vegtypen["vegtypen_list"] = subset_vegtypen.apply(
            lambda row: [row[col] for col in vegtype_col], axis=1
        )
        subset_vegtypen = subset_vegtypen.explode("vegtypen_list")[
            [ElmID_col, "vegtypen_list"]
        ]
        subset_vegtypen["vegtypen_list"] = vegtype_cls.opschonen_series(
            subset_vegtypen["vegtypen_list"]
        )

        subset_perc = gdf[perc_col + [ElmID_col]].copy()
        subset_perc["perc_list"] = subset_perc.apply(
            lambda row: [row[col] for col in perc_col], axis=1
        )
        subset_perc = subset_perc.explode("perc_list")[[ElmID_col, "perc_list"]]

        combined = pd.DataFrame(
            {
                ElmID_col: subset_vegtypen[ElmID_col],
                "vegtypen_list": subset_vegtypen["vegtypen_list"],
                "perc_list": subset_perc["perc_list"],
            }
        )
    elif vegtype_col_format == "single":
        subset_vegtypen = gdf[[ElmID_col, vegtype_col]].copy()
        subset_vegtypen["vegtypen_list"] = subset_vegtypen[vegtype_col].str.split(
            split_char
        )
        subset_vegtypen = subset_vegtypen.explode("vegtypen_list")[
            [ElmID_col, "vegtypen_list"]
        ]
        subset_vegtypen["vegtypen_list"] = vegtype_cls.opschonen_series(
            subset_vegtypen["vegtypen_list"]
        )

        subset_perc = gdf[[ElmID_col, perc_col]].copy()
        subset_perc["perc_list"] = subset_perc[perc_col].str.split(split_char)
        subset_perc = subset_perc.explode("perc_list")[[ElmID_col, "perc_list"]]

        combined = pd.DataFrame(
            {
                ElmID_col: subset_vegtypen[ElmID_col],
                "vegtypen_list": subset_vegtypen["vegtypen_list"],
                "perc_list": subset_perc["perc_list"],
            }
        )
    else:
        raise ValueError(
            f"vegtype_col_format moet 'single' of 'multi' zijn, maar is nu '{vegtype_col_format}'"
        )

    vegtypeinfos = (
        combined.groupby(ElmID_col)
        .apply(
            lambda rows: VegTypeInfo.create_vegtypen_list_from_rows(
                rows,
                perc_col="perc_list",
                SBB_col="vegtypen_list" if vegtype_cls == _SBB else None,
                VvN_col="vegtypen_list" if vegtype_cls == _VvN else None,
            )
        )
        .reset_index()
        .rename(columns={0: "VegTypeInfo"})
    )

    return gdf.merge(vegtypeinfos, on=ElmID_col).VegTypeInfo


def fill_in_percentages(
    row: gpd.GeoSeries,
    vegtype_col_format: Literal["single", "multi"],
    split_char: Optional[str],
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

    if vegtype_col_format == "multi":
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
    elif vegtype_col_format == "single":
        # Uitzoeken hoeveel vegtypen er zijn
        nr_of_vvn = (
            len(row[vvn_col].split(split_char)) if vvn_col and row[vvn_col] else 0
        )
        nr_of_sbb = (
            len(row[sbb_col].split(split_char)) if sbb_col and row[sbb_col] else 0
        )
        max_veg_types = max(nr_of_vvn, nr_of_sbb)

        # Percentages berekenen en toekennen
        if max_veg_types == 0:
            row[perc_col] = 0
        else:
            row[perc_col] = split_char.join([str(100 / max_veg_types)] * max_veg_types)
    else:
        raise ValueError(
            f"vegtype_col_format moet 'single' of 'multi' zijn, maar is nu '{vegtype_col_format}'"
        )
    return row


def combine_vegtypeinfos_columns(
    sbb_vegtypeinfo: pd.Series, vvn_vegtypeinfo: pd.Series
) -> pd.Series:
    """
    Combineert 2 series VegTypeInfo naar 1, waarbij de SBB van
    de eerste series en de VvN van de tweede series worden behouden
    """
    df = pd.DataFrame({"SBB": sbb_vegtypeinfo, "VvN": vvn_vegtypeinfo})

    combined = df.apply(
        combine_vegtypeinfos_row,
        axis=1,
    )
    return combined


def combine_vegtypeinfos_row(row: gpd.GeoSeries) -> List[VegTypeInfo]:
    """
    Combineert de SBB en VvN VegTypeInfos uit een rij naar 1 VegTypeInfo
    """
    sbb_vegtypeinfo = row["SBB"]
    vvn_vegtypeinfo = row["VvN"]

    # Check dat er geen NaNs zijn
    if not sbb_vegtypeinfo:
        return vvn_vegtypeinfo
    if not vvn_vegtypeinfo:
        return sbb_vegtypeinfo

    combined = list(zip(sbb_vegtypeinfo, vvn_vegtypeinfo))

    # Check dat de percentages gelijk zijn
    if not all(info[0].percentage == info[1].percentage for info in combined):
        raise ValueError(
            f"""Percentages in te combineren VegTypeInfos zijn niet gelijk.
                         SBB: {sbb_vegtypeinfo}
                         VvN: {vvn_vegtypeinfo}"""
        )

    return [
        VegTypeInfo(
            percentage=info[0].percentage,
            SBB=info[0].SBB,
            VvN=info[1].VvN,
        )
        for info in combined
    ]


def haal_complexen_door_functie(complexen: List[List], func) -> List[List]:
    """
    Haal alle habitatvoorstellen door een functie heen
    """
    return [func(complex) for complex in complexen]


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
    keuze_en_vegtypeinfo = list(zip(row["HabitatKeuze"], row["VegTypeInfo"]))
    # Sorteer op basis van de habitatkeuze (idx 0)
    sorted_keuze_en_vegtypeinfo = sorted(keuze_en_vegtypeinfo, key=rank_habitatkeuzes)

    row["HabitatKeuze"], row["VegTypeInfo"] = zip(*sorted_keuze_en_vegtypeinfo)
    # Tuples uit zip omzetten naar lists
    row["HabitatKeuze"], row["VegTypeInfo"] = list(row["HabitatKeuze"]), list(
        row["VegTypeInfo"]
    )
    return row


def hab_as_final_format(print_info: tuple, idx: int, opp: float) -> pd.Series:
    """
    Dit moet echt netter :)
    """
    # TODO: het 1 voorstel geval qua output unifien met meerdere voorstellen zodat het enkel afhangt van status wat er geprint wordt
    # TODO: Dit kan allemaal naar HabitatKeuze (.as_final_form() ofzo)

    keuze, vegtypeinfo = print_info

    # Er is 1 HabitatVoorstel
    if len(keuze.habitatvoorstellen) == 1:
        if keuze.status in [
            KeuzeStatus.DUIDELIJK,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
            KeuzeStatus.PLACEHOLDER_CRITERIA,
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
        ]:
            voorstel = keuze.habitatvoorstellen[0]
            series_dict = {
                f"Habtype{idx}": voorstel.habtype,
                f"Perc{idx}": vegtypeinfo.percentage,
                f"Opp{idx}": opp * vegtypeinfo.percentage,
                # f"ISHD{idx}" NOTE: Deze hoeft niet denk ik
                f"Kwal{idx}": voorstel.kwaliteit.as_letter()
                if isinstance(voorstel.kwaliteit, Kwaliteit)
                else None,
                f"Opm{idx}": keuze.opmerking,
                # f"Bron{idx}" NOTE: Ik weet niet wat ik hier moet zetten
                # f"HABcombi{idx}" NOTE: Deze hoeft niet denk ik
                f"VvN{idx}": str(voorstel.onderbouwend_vegtype)
                if isinstance(voorstel.onderbouwend_vegtype, _VvN)
                else None,
                f"SBB{idx}": str(voorstel.onderbouwend_vegtype)
                if isinstance(voorstel.onderbouwend_vegtype, _SBB)
                else None,
                # f"P{idx}" NOTE: Deze is altijd hetzelfde als Perc toch?
                # f"VEGlok{idx}" NOTE: Doen we voor nu nog even niet
                f"_Status{idx}": str(keuze.status),
                f"_VvNdftbl{idx}": str(
                    [str(voorstel.vegtype_in_dt), voorstel.idx_in_dt]
                )
                if isinstance(voorstel.vegtype_in_dt, _VvN)
                else None,
                f"_SBBdftbl{idx}": str(
                    [str(voorstel.vegtype_in_dt), voorstel.idx_in_dt]
                )
                if isinstance(voorstel.vegtype_in_dt, _SBB)
                else None,
                f"_VgTypInf{idx}": str(vegtypeinfo),
                f"_ChkNodig{idx}": False,
            }

            if keuze.status == KeuzeStatus.GEEN_KLOPPENDE_MITSEN:
                series_dict[f"Habtype{idx}"] = "H0000"
                series_dict[f"Kwal{idx}"] = None
            if (
                keuze.status == KeuzeStatus.PLACEHOLDER_CRITERIA
                or keuze.status == KeuzeStatus.WACHTEN_OP_MOZAIEK
            ):
                series_dict[f"Habtype{idx}"] = "HXXXX"
                series_dict[f"Kwal{idx}"] = "Onbekend"
                series_dict[f"_ChkNodig{idx}"] = True

            return pd.Series(series_dict)

        assert (
            False
        ), f"Er is 1 habitatkeuze maar KeuzeStatus {keuze.status} is niet DUIDELIJK, VEGTYPEN_NIET_IN_DEFTABEL of GEEN_KLOPPENDE_MITSEN"

    if keuze.status in [
        KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
        KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
        KeuzeStatus.PLACEHOLDER_CRITERIA,
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
            f"Habtype{idx}": str(
                [voorstel[0] for voorstel in voorgestelde_hab_en_kwal]
            ),
            f"Perc{idx}": str(vegtypeinfo.percentage),
            f"Opp{idx}": str(opp * vegtypeinfo.percentage),
            # f"ISHD{idx}" NOTE: Deze hoeft niet denk ik
            f"Kwal{idx}": str(
                [
                    (
                        voorstel[1].as_letter()
                        if isinstance(voorstel[1], Kwaliteit)
                        else None
                    )
                    for voorstel in voorgestelde_hab_en_kwal
                ]
            ),
            f"Opm{idx}": keuze.opmerking,
            # f"Bron{idx}" NOTE: Ik weet niet wat ik hier moet zetten
            # f"HABcombi{idx}" NOTE: Deze hoeft niet denk ik
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
            # f"P{idx}" NOTE: Deze is altijd hetzelfde als Perc toch?
            # f"VEGlok{idx}" NOTE: Doen we voor nu nog even niet
            f"_Status{idx}": str(keuze.status),
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
            f"_ChkNodig{idx}": False,
        }

        if keuze.status == KeuzeStatus.GEEN_KLOPPENDE_MITSEN:
            series_dict[f"Habtype{idx}"] = "H0000"
            series_dict[f"Kwal{idx}"] = None
        if keuze.status in [
            KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
            KeuzeStatus.PLACEHOLDER_CRITERIA,
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
        ]:
            series_dict[f"Habtype{idx}"] = "HXXXX"
            series_dict[f"Kwal{idx}"] = "Onbekend"
            series_dict[f"_ChkNodig{idx}"] = True

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


def finalize_final_format(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Reorder de kolommen van een dataframe conform het Gegevens Leverings Protocol
    Resultaat zal zijn:
    Area   Opm   geometry   Habtype1   Perc1   Opp1   Kwal1   VvN1   SBB1   Habtype2   Perc2   Opp2...
    """
    new_columns = ["Area", "Opm", "Datum", "geometry", "_ChkNodig"]
    n_habtype_blocks = len([i for i in gdf.columns if "Habtype" in i])
    for i in range(1, n_habtype_blocks + 1):
        new_columns = new_columns + [
            f"Habtype{i}",
            f"Perc{i}",
            f"Opp{i}",
            f"Kwal{i}",
            f"Opm{i}",
            f"VvN{i}",
            f"SBB{i}",
            f"_Status{i}",
            f"_VvNdftbl{i}",
            f"_SBBdftbl{i}",
            f"_VgTypInf{i}",
            f"_ChkNodig{i}",
        ]
    return gdf[new_columns]


def fix_crs(
    gdf: gpd.GeoDataFrame, shape_path: Path = "onbekend.shp"
) -> gpd.GeoDataFrame:
    """
    Geeft voor gdfs zonder crs een warning en zet ze om naar EPSG:28992
    Zet gdfs met een andere crs dan EPSG:28992 om naar EPSG:28992
    """
    if gdf.crs is None:
        warnings.warn(f"CRS van {shape_path} was None en is nu gelezen als EPSG:28992")
        gdf = gdf.set_crs(epsg=28992)
    elif gdf.crs.to_epsg() != 28992:
        # NOTE: @reviewer
        # NOTE: @reviewer   Moet hier een warning bij? Lijkt me van niet, maar ik weet niet in hoeverre
        # NOTE: @reviewer   het omzetten van crs eventuele problemen kan geven
        # NOTE: @reviewer
        # warnings.warn(
        #     f"CRS van {shape_path} was EPSG:{gdf.crs.to_epsg()} en is nu omgezet naar EPSG:28992"
        # )
        gdf = gdf.to_crs(epsg=28992)
    return gdf


def _multi_to_single(
    gdf: gpd.GeoDataFrame,
    sbb_of_vvn: Literal["VvN", "SBB", "beide"],
    SBB_col: Optional[str] = None,
    VvN_col: Optional[str] = None,
    split_char: Optional[str] = None,
    perc_col: Optional[str] = None,
) -> gpd.GeoDataFrame:
    """
    Converteert een "multi" kolomformat dataframe naar een "single" kolomformat dataframe
    De nieuwe "single" format kolommen heten SBB_single, VvN_single en perc_single
    # TODO: Hier kan informatieverlies plaatsvinden, we moeten dit de andere kant op doen
    """
    if sbb_of_vvn in ["SBB", "beide"]:
        SBB_col = SBB_col.split(split_char)
        gdf["SBB_single"] = gdf.apply(
            lambda row: split_char.join(
                [row[col] for col in SBB_col if pd.notna(row[col])]
            ),
            axis=1,
        )
    if sbb_of_vvn in ["VvN", "beide"]:
        VvN_col = VvN_col.split(split_char)
        gdf["VvN_single"] = gdf.apply(
            lambda row: split_char.join(
                [row[col] for col in VvN_col if pd.notna(row[col])]
            ),
            axis=1,
        )
    if perc_col:
        perc_col = perc_col.split(split_char)
        gdf["perc_single"] = gdf.apply(
            lambda row: split_char.join(
                [str(row[col]) for col in perc_col if pd.notna(row[col])]
            ),
            axis=1,
        )
    return gdf


class Kartering:
    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # NOTE: evt iets van self.stage = lokaal/sbb/vvn ofzo? Enum?
        #       Misschien een dict met welke stappen gedaan zijn?

    @classmethod
    def from_access_db(
        cls,
        shape_path: Path,
        shape_elm_id_column: str,
        access_csvs_path: Path,
        opmerkingen_column: Optional[str] = "Opmerking",
        datum_column: Optional[str] = "Datum",
    ) -> "Kartering":
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

        element = pd.read_csv(
            access_csvs_path / "Element.csv",
            usecols=["ElmID", "intern_id", "Locatietype"],
            dtype={"ElmID": int, "intern_id": int, "Locatietype": str},
        )
        # Uitfilteren van lijnen
        element["Locatietype"] = element["Locatietype"].str.lower()
        element = element[element.Locatietype == "v"][["ElmID", "intern_id"]]

        kart_veg = pd.read_csv(
            access_csvs_path / "KarteringVegetatietype.csv",
            usecols=["Locatie", "Vegetatietype", "Bedekking_num"],
            dtype={"Locatie": int, "Vegetatietype": str, "Bedekking_num": int},
        )
        # BV voor GM2b -> Gm2b (elmid 10219 in ruitenaa2020)
        kart_veg.Vegetatietype = kart_veg.Vegetatietype.str.lower()

        vegetatietype = pd.read_csv(
            access_csvs_path / "VegetatieType.csv",
            usecols=["Code", "SbbType"],
            dtype={"Code": str, "SbbType": int},
        )
        vegetatietype.Code = vegetatietype.Code.str.lower()

        sbbtype = pd.read_csv(
            access_csvs_path / "SbbType.csv",
            usecols=["Cata_ID", "Code"],
            dtype={"Cata_ID": int, "Code": str},
        )
        # Code hernoemen want er zit al een "Code" in Vegetatietype.csv
        sbbtype = sbbtype.rename(columns={"Code": "Sbb"})

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
            message = f"Er is geen 1 op 1 relatie tussen {shape_elm_id_column} in de shapefile en ElmID in de Element.csv."
            if not gdf[shape_elm_id_column].is_unique:
                dubbele_elmid = gdf[shape_elm_id_column][
                    gdf[shape_elm_id_column].duplicated()
                ].to_list()[:10]
                message += f" Er zitten dubbelingen in de shapefile, bijvoorbeeld {shape_elm_id_column}: {dubbele_elmid}."
            if not element.ElmID.is_unique:
                dubbele_elmid = element.ElmID[element.ElmID.duplicated()].to_list()[:10]
                message += f" Er zitten dubbelingen in Element.csv, bijvoorbeeld ElmID: {dubbele_elmid}."
            raise ValueError(message) from e

        # SBB code toevoegen aan KarteringVegetatietype
        kart_veg = kart_veg.merge(
            vegetatietype, left_on="Vegetatietype", right_on="Code", how="left"
        )
        kart_veg = kart_veg.merge(
            sbbtype, left_on="SbbType", right_on="Cata_ID", how="left"
        )

        # Opschonen SBB codes
        kart_veg["Sbb"] = _SBB.opschonen_series(kart_veg["Sbb"])

        # Groeperen van alle verschillende SBBs per Locatie
        grouped_kart_veg = (
            kart_veg.groupby("Locatie")
            .apply(
                VegTypeInfo.create_vegtypen_list_from_rows,
                perc_col="Bedekking_num",
                SBB_col="Sbb",
            )
            .reset_index(name="VegTypeInfo")
        )

        # Joinen van de SBBs aan de gdf
        gdf = gdf.merge(
            grouped_kart_veg, left_on="intern_id", right_on="Locatie", how="left"
        )

        # We laten alle NA vegtype-informatie vallen - dit kan komen door geometry die lijnen zijn in plaats van vormen,
        # maar ook aan ontbrekende waarden in een van de csv-bestanden.
        if gdf.VegTypeInfo.isnull().any():
            # TODO: Zodra we een mooi logsysteem hebben, moeten we dit loggen in plaats van het te printen.
            # NOTE: Moet dit een warning zijn?
            print(
                f"Er zijn {gdf.VegTypeInfo.isnull().sum()} vlakken zonder VegTypeInfo in {shape_path}. Deze worden verwijderd."
            )
            print(
                f"De eerste paar ElmID van de verwijderde vlakken zijn: {gdf[gdf.VegTypeInfo.isnull()].ElmID.head().to_list()}"
            )
            gdf = gdf.dropna(subset=["VegTypeInfo"])

        return cls(gdf)

    def _multi_to_single(
        self,
        gdf: gpd.GeoDataFrame,
        sbb_of_vvn: Literal["VvN", "SBB", "beide"],
        SBB_col: Optional[str] = None,
        VvN_col: Optional[str] = None,
        split_char: Optional[str] = None,
        perc_col: Optional[str] = None,
    ) -> gpd.GeoDataFrame:
        """
        Converts a "multi" formatted gdf to a "single" formatted gdf
        """
        if sbb_of_vvn in ["SBB", "beide"]:
            SBB_col = SBB_col.split(split_char)
            gdf["SBB_single"] = gdf.apply(
                lambda row: split_char.join(
                    [row[col] for col in SBB_col if pd.notna(row[col])]
                ),
                axis=1,
            )
        if sbb_of_vvn in ["VvN", "beide"]:
            VvN_col = VvN_col.split(split_char)
            gdf["VvN_single"] = gdf.apply(
                lambda row: split_char.join(
                    [row[col] for col in VvN_col if pd.notna(row[col])]
                ),
                axis=1,
            )
        if perc_col:
            perc_col = perc_col.split(split_char)
            gdf["perc_single"] = gdf.apply(
                lambda row: split_char.join(
                    [row[col] for col in perc_col if pd.notna(row[col])]
                ),
                axis=1,
            )
        return gdf

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
    ) -> "Kartering":
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
                Er worden nieuwe waarden voor {ElmID_col} gemaakt en gebruikt.
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

        gdf = fix_crs(gdf, shape_path)

        # TODO: single -> multi

        # TODO: opschonen hier doen ipv in ingest vegtype
        # TODO: opschonen hier doen ipv in ingest vegtype
        # TODO: opschonen hier doen ipv in ingest vegtype
        # Opschonen
        # if sbb_cols:
        #     gdf[sbb_cols] = gdf[sbb_cols].apply(_SBB.opschonen_series)
        
        # if vvn_cols:
        #     gdf[vvn_cols] = gdf[vvn_cols].apply(_VvN.opschonen_series)

        # Als er geen datum of opmerking kolom is, dan maken we die en vullen we deze met None
        datum_col = "Datum" if datum_col is None else datum_col
        opmerking_col = "Opmerking" if opmerking_col is None else opmerking_col
        for col in [datum_col, opmerking_col]:
            if col not in gdf.columns:
                gdf[col] = None

        # Standardiseren van kolomnamen
        # NOTE: Pandera..?
        gdf = gdf.rename(columns={datum_col: "Datum", opmerking_col: "Opmerking"})
        gdf["Opp"] = gdf["geometry"].area

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
                    row, vegtype_col_format, split_char, perc_col, SBB_col, VvN_col
                ),
                axis=1,
            )

        ###############
        ##### Inlezen van de vegetatietypen
        ###############

        if sbb_of_vvn in ["SBB", "beide"]:
            sbb_vegtypeinfos = ingest_vegtype_column(
                gdf,
                ElmID_col,
                vegtype_col_format,
                SBB_col,
                _SBB,
                perc_col,
                split_char,
            )
            # Als het enkel SBB is zijn we klaar
            if sbb_of_vvn != "beide":
                gdf["VegTypeInfo"] = sbb_vegtypeinfos

        if sbb_of_vvn in ["VvN", "beide"]:
            vvn_vegtypeinfos = ingest_vegtype_column(
                gdf,
                ElmID_col,
                vegtype_col_format,
                VvN_col,
                _VvN,
                perc_col,
                split_char,
            )
            # Als het enkel VvN is zijn we klaar
            if sbb_of_vvn != "beide":
                gdf["VegTypeInfo"] = vvn_vegtypeinfos

        # Als we beide hebben moeten we de VegTypeInfos samenvoegen
        if sbb_of_vvn == "beide":
            gdf["VegTypeInfo"] = combine_vegtypeinfos_columns(
                sbb_vegtypeinfos, vvn_vegtypeinfos
            )

        return cls(gdf)

    def apply_wwl(self, wwl: pd.DataFrame, override_existing_VvN: bool = False) -> None:
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

    def apply_deftabel(self, dt: pd.DataFrame) -> None:
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

        ### Habitatkeuzes bepalen
        self.gdf["HabitatKeuze"] = self.gdf["HabitatVoorstel"].apply(
            haal_complexen_door_functie, args=[habitatkeuze_obv_mitsen]
        )

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
            ["Opp", "Opmerking", "Datum", "geometry", "VegTypeInfo", "HabitatKeuze"]
        ].copy()

        # Sorteer de keuzes eerst op niet-H0000-zijn, dan op percentage, dan op kwaliteit
        base = base.apply(sorteer_vegtypeinfos_habvoorstellen, axis=1)

        base = base.rename(columns={"Opp": "Area", "Opmerking": "Opm"})

        final = pd.concat([base, base.apply(self.row_to_final_format, axis=1)], axis=1)
        final["_ChkNodig"] = final.apply(bepaal_ChckNodig, axis=1)
        final = finalize_final_format(final)
        return final

    def row_to_final_format(self, row) -> pd.Series:
        """
        Maakt van een rij een dataseries met blokken kolommen volgens het Gegevens Leverings Protocol (Bijlage 3a)
        """
        keuzes = row["HabitatKeuze"]
        vegtypeinfos = row["VegTypeInfo"]
        assert len(keuzes) > 0, "Er vlakken zonder habitatkeuze"
        assert len(keuzes) == len(
            vegtypeinfos
        ), "Er zijn niet evenveel habitatkeuzes als vegtypeinfos"

        # NOTE: Misschien een class maken van print_info als er nog meer bijkomt?
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

    def __getitem__(self, item):
        return Geometrie(self.gdf.iloc[item])
