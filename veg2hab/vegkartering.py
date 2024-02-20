import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd

from veg2hab.criteria import FGRCriterium
from veg2hab.enums import Kwaliteit
from veg2hab.fgr import FGR
from veg2hab.habitat import (
    HabitatKeuze,
    HabitatVoorstel,
    KeuzeStatus,
    habitatkeuze_obv_mitsen,
    is_criteria_type_present,
    rank_habitatkeuzes,
)
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import VvN as _VvN
from veg2hab.vegetatietypen import opschonen_SBB_pandas_series


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

    @classmethod
    def from_str_vegtypes(
        cls, percentage: int, VvN_strings: List[str] = [], SBB_strings: List[str] = []
    ):
        """
        Aanmaken vanuit string vegetatietypen
        """
        assert len(SBB_strings) <= 1, "Er kan niet meer dan 1 SBB type zijn"

        return cls(
            percentage=percentage,
            VvN=[_VvN(i) for i in VvN_strings],
            SBB=[_SBB(i) for i in SBB_strings],
        )

    @classmethod
    def create_list_from_access_rows(cls, rows: pd.DataFrame):
        """
        Maakt van alle rijen met vegetatietypes (van een vlak) een lijst van VegetatieTypeInfo objecten
        """
        lst = []
        for row in rows.itertuples():
            if pd.isnull(row.Sbb):
                # NA SBB moet geen SBB object worden
                lst.append(cls.from_str_vegtypes(row.Bedekking_num))
            else:
                lst.append(
                    cls.from_str_vegtypes(row.Bedekking_num, SBB_strings=[row.Sbb])
                )
        return lst

    def __str__(self):
        return f"({self.percentage}%, VvN: {[str(x) for x in self.VvN]}, SBB: {[str(x) for x in self.SBB]})"

    def __hash__(self):
        return hash((self.percentage, tuple(self.VvN), tuple(self.SBB)))


class Geometrie:
    """Een shape/rij uit de vegetatiekartering.
    Deze bevat of een VvN of een SBB code en een geometrie.
    """

    data: gpd.GeoSeries  # (pandas series?)

    def __init__(self, data: gpd.GeoSeries):
        self.data = data


def haal_complexen_door_functie(complexen: List[List[HabitatVoorstel]], func):
    """
    Haal alle habitatvoorstellen door een functie heen
    """
    return [func(complex) for complex in complexen]


def sorteer_vegtypeinfos_habvoorstellen(row: gpd.GeoSeries):
    """
    Sorteert de habitatkeuze en vegtypeinfo van een rij op basis van de habitatkeuze
    """
    combined = list(zip(row["HabitatKeuze"], row["VegTypeInfo"]))
    # Sorteer op basis van de habitatkeuze (idx 0)
    sorted_combined = sorted(combined, key=rank_habitatkeuzes)

    row["HabitatKeuze"], row["VegTypeInfo"] = zip(*sorted_combined)
    # Tuples uit zip omzetten naar lists
    row["HabitatKeuze"], row["VegTypeInfo"] = list(row["HabitatKeuze"]), list(
        row["VegTypeInfo"]
    )
    return row


def hab_as_final_format(print_info: tuple, idx: int, opp: float):
    # TODO: het 1 voorstel geval qua output unifien met meerdere voorstellen zodat het enkel afhangt van status wat er geprint wordt

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


def bepaal_ChckNodig(row: gpd.GeoSeries):
    """
    Bepaalt of een rij een habitattypekartering een handmatige controle nodig heeft
    """
    check_nodigs = [col for col in row.index if "_ChkNodig" in col]
    if any(row[check_nodig] == True for check_nodig in check_nodigs):
        return True
    return False


def reorder_columns_final_format(df: pd.DataFrame):
    """
    Reorder de kolommen van een dataframe conform het Gegevens Leverings Protocol
    Result wil be:
    Area   Opm   geometry   Habtype1   Perc1   Opp1   Kwal1   VvN1   SBB1   Habtype2   Perc2   Opp2...
    """
    new_columns = ["Area", "Opm", "geometry", "_ChkNodig"]
    n_habtype_blocks = len([i for i in df.columns if "Habtype" in i])
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
    return df[new_columns]


class Kartering:
    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Validation van de gdf
        self.validate()

        # NOTE: evt iets van self.stage = lokaal/sbb/vvn ofzo? Enum?
        #       Misschien een dict met welke stappen gedaan zijn?

    @classmethod
    def from_access_db(
        cls, shape_path: Path, shape_elm_id_column: str, access_csvs_path: Path
    ):
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile en
        een access database die al is opgedeeld in losse csv bestanden.

        # .shp shp_elm_id_column -> ElmID in Element.csv voor intern_id -> Locatie in KarteringVegetatietype.csv voor Vegetatietype ->
        #      -> Code in Vegetatietype.csv voor SbbType -> Cata_ID in SsbType.csv voor Code (hernoemd naar Sbb)
        """
        gdf = gpd.read_file(shape_path)

        element = pd.read_csv(
            access_csvs_path / "Element.csv",
            usecols=["ElmID", "intern_id"],
            dtype={"ElmID": int, "intern_id": int},
        )

        kart_veg = pd.read_csv(
            access_csvs_path / "KarteringVegetatietype.csv",
            usecols=["Locatie", "Vegetatietype", "Bedekking_num"],
            dtype={"Locatie": int, "Vegetatietype": str, "Bedekking_num": int},
        )

        vegetatietype = pd.read_csv(
            access_csvs_path / "VegetatieType.csv",
            usecols=["Code", "SbbType"],
            dtype={"Code": str, "SbbType": int},
        )

        sbbtype = pd.read_csv(
            access_csvs_path / "SbbType.csv",
            usecols=["Cata_ID", "Code"],
            dtype={"Cata_ID": int, "Code": str},
        )
        # Code hernoemen want er zit al een "Code" in Vegetatietype.csv
        sbbtype = sbbtype.rename(columns={"Code": "Sbb"})

        # Intern ID toevoegen aan de gdf
        gdf = gdf.merge(
            element, left_on=shape_elm_id_column, right_on="ElmID", how="left"
        )

        # SBB code toevoegen aan KarteringVegetatietype
        kart_veg = kart_veg.merge(
            vegetatietype, left_on="Vegetatietype", right_on="Code", how="left"
        )
        kart_veg = kart_veg.merge(
            sbbtype, left_on="SbbType", right_on="Cata_ID", how="left"
        )

        # Opschonen SBB codes
        kart_veg["Sbb"] = opschonen_SBB_pandas_series(kart_veg["Sbb"])

        # Groeperen van alle verschillende SBBs per Locatie
        grouped_kart_veg = (
            kart_veg.groupby("Locatie")
            .apply(VegTypeInfo.create_list_from_access_rows)
            .reset_index(name="VegTypeInfo")
        )

        # Joinen van de SBBs aan de gdf
        gdf = gdf.merge(
            grouped_kart_veg, left_on="intern_id", right_on="Locatie", how="left"
        )

        return cls(gdf)

    @classmethod
    def from_shapefile(cls, shape_path):
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile.
        """
        gdf = gpd.read_file(shape_path)
        return cls(gdf)

    def apply_wwl(self, wwl: pd.DataFrame):
        """
        Pas een was-wordt lijst toe op de kartering om VvN toe te voegen aan SBB-only
        """
        assert "VegTypeInfo" in self.gdf.columns, "Er is geen kolom met VegTypeInfo"
        self.gdf["VegTypeInfo"] = self.gdf["VegTypeInfo"].apply(
            wwl.toevoegen_VvN_aan_List_VegTypeInfo
        )

    def apply_deftabel(self, dt: pd.DataFrame):
        """
        Pas een definitietabel toe op de kartering om habitatvoorstellen toe te voegen
        """
        assert "VegTypeInfo" in self.gdf.columns, "Er is geen kolom met VegTypeInfo"
        # NOTE: iets wat vast stelt dat er tenminste 1 VegTypeInfo met een VvN is, zo niet geef warning?

        self.gdf["HabitatVoorstel"] = self.gdf["VegTypeInfo"].apply(
            lambda infos: [dt.find_habtypes(info) for info in infos]
        )

    def check_mitsen(self, fgr: FGR):
        """
        Check of de mitsen in de habitatvoorstellen van de kartering voldoen.
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

    def as_final_format(self):
        """
        Output de kartering conform de beschrijving voor habitattypekarteringen zoals beschreven
        in het Gegevens Leverings Protocol (Bijlage 3a)
        """
        assert (
            "HabitatKeuze" in self.gdf.columns
        ), "Er is geen kolom met definitieve habitatvoorstellen"

        # Base dataframe conform Gegevens Leverings Protocol maken
        base = self.gdf[
            ["Opp", "Opmerking", "geometry", "VegTypeInfo", "HabitatKeuze"]
        ].copy()

        # Sorteer de keuzes eerst op niet-H0000-zijn, dan op percentage, dan op kwaliteit
        base = base.apply(sorteer_vegtypeinfos_habvoorstellen, axis=1)

        base = base.rename(columns={"Opp": "Area", "Opmerking": "Opm"})

        final = pd.concat([base, base.apply(self.row_to_final_format, axis=1)], axis=1)
        final["_ChkNodig"] = final.apply(bepaal_ChckNodig, axis=1)
        final = reorder_columns_final_format(final)
        return final

    def row_to_final_format(self, row):
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

    def final_format_to_shp(self, path: Path):
        """
        Slaat de kartering op in een shapefile
        """
        final = self.as_final_format()
        gdf = gpd.GeoDataFrame(final, geometry="geometry")
        gdf.to_file(path)

    def __len__(self):
        return len(self.gdf)

    def __getitem__(self, item):
        return Geometrie(self.gdf.iloc[item])

    def validate(self):
        pass
        # Validation error als t foute boel is

        # Validate aanwezigheid vvn/sbb/geometry kolommen (en evt nog andere die nodig zijn)

        # Validate dat we of vvn of sbb hebben

        # Validate dat het valide codes zijn

        # Validate dat de geometrie een 2D multipolygon is

        # Validate dat de geometrie valide is (geen overlap, geen self intersection, etc)

        # Validate dat t rijksdriehoek is
