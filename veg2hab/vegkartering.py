import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Type, Union

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
    def create_list_from_access_rows(
        cls,
        rows: pd.DataFrame,
        perc_col: str,
        SBB_col: Optional[str] = None,
        VvN_col: Optional[str] = None,
    ):
        """
        Maakt van alle rijen met vegetatietypes (van een vlak) een lijst van VegetatieTypeInfo objecten
        """
        assert (
            SBB_col or VvN_col and not (SBB_col and VvN_col)
        ), f"Er moet een SBB of VvN kolom zijn, maar niet beide. Nu is SBB_col={SBB_col} en VvN_col={VvN_col}"
        vegtype_col = VvN_col if VvN_col else SBB_col
        lst = []

        for _, row in rows.iterrows():
            if pd.isnull(row[vegtype_col]):
                # NA SBB moet geen VegTypeInfo object worden
                lst.append(cls.from_str_vegtypes(row[perc_col]))
            else:
                lst.append(
                    cls.from_str_vegtypes(row[perc_col], SBB_strings=[row[vegtype_col]])
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


def ingest_vegtype_column(
    gdf: gpd.GeoDataFrame,
    ElmID_col: str,
    vegtype_col: str,
    vegtype_cls: Union[Type[_SBB], Type[_VvN]],
    vegtype_split_char: Optional[str] = None,
    # percentage_col: Optional[str] = None, TODO: add support for already existing percentage_col
):
    """
    Leest een kolom met vegetatietypen in en maakt hier VegTypeInfo objecten van
    De kolom wordt eerst gesplitst op een opgegeven karakter (voor complexen (bv "16aa2+15aa")))
    Hierna wordt de kolom geexplode, worden er VegTypeInfo gemaakt van alle vegtypen en deze worden weer op ElmID samengevoegd
    """
    # TODO: Add support for vegtypen over multiple columns.
    gdf = gdf.copy()  # Anders krijgen we een SettingWithCopyWarning

    if vegtype_split_char:
        gdf["split_vegtypen"] = gdf[vegtype_col].str.split(vegtype_split_char)
    else:
        gdf["split_vegtypen"] = gdf[vegtype_col]
    exploded = gdf.explode("split_vegtypen")
    gdf = gdf.drop(columns=["split_vegtypen"])

    # TODO: voeg ondersteuning toe voor al bestaande percentage_col
    # Als er geen percentagekolom is, voegen we deze toe door de ruimte in elke vorm gelijkmatig te verdelen
    if True:  # not percentage_col:
        exploded["percentage"] = exploded.groupby(ElmID_col)[ElmID_col].transform(
            lambda x: 100.0 / len(x)
        )

    exploded["split_vegtypen"] = vegtype_cls.opschonen_series(
        exploded["split_vegtypen"]
    )
    vegtypeinfos = (
        exploded.groupby(ElmID_col)
        .apply(
            VegTypeInfo.create_list_from_access_rows,
            perc_col="percentage",
            SBB_col="split_vegtypen" if vegtype_cls == _SBB else None,
            VvN_col="split_vegtypen" if vegtype_cls == _VvN else None,
        )
        .reset_index(name="VegTypeInfo")
        .VegTypeInfo
    )

    gdf["VegTypeInfo"] = vegtypeinfos

    return gdf


def haal_complexen_door_functie(complexen: List[List[HabitatVoorstel]], func):
    """
    Haal alle habitatvoorstellen door een functie heen
    """
    return [func(complex) for complex in complexen]


def sorteer_vegtypeinfos_habvoorstellen(row: gpd.GeoSeries):
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


def hab_as_final_format(print_info: tuple, idx: int, opp: float):
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
    Resultaat zal zijn:
    Area   Opm   geometry   Habtype1   Perc1   Opp1   Kwal1   VvN1   SBB1   Habtype2   Perc2   Opp2...
    """
    new_columns = ["Area", "Opm", "Datum", "geometry", "_ChkNodig"]
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
        cls,
        shape_path: Path,
        shape_elm_id_column: str,
        access_csvs_path: Path,
        opmerkingen_column: Optional[str] = "Opmerking",
        datum_column: Optional[str] = "Datum",
    ):
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile en
        een access database die al is opgedeeld in losse csv bestanden.

        # .shp shp_elm_id_column -> ElmID in Element.csv voor intern_id -> Locatie in KarteringVegetatietype.csv voor Vegetatietype ->
        #      -> Code in Vegetatietype.csv voor SbbType -> Cata_ID in SsbType.csv voor Code (hernoemd naar Sbb)
        """
        gdf = gpd.read_file(shape_path)

        # Subsetten van kolommen
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
            usecols=["ElmID", "intern_id"],
            dtype={"ElmID": int, "intern_id": int},
        )

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
        kart_veg["Sbb"] = _SBB.opschonen_series(kart_veg["Sbb"])

        # Groeperen van alle verschillende SBBs per Locatie
        grouped_kart_veg = (
            kart_veg.groupby("Locatie")
            .apply(
                VegTypeInfo.create_list_from_access_rows,
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
                f"Er zijn {gdf.VegTypeInfo.isnull().sum()} vlakken zonder VegTypeInfo. Deze worden verwijderd."
            )
            print(
                f"De eerste paar ElmID van de verwijderde vlakken zijn: {gdf[gdf.VegTypeInfo.isnull()].ElmID.head().to_list()}"
            )
            gdf = gdf.dropna(subset=["VegTypeInfo"])

        return cls(gdf)

    @classmethod
    def from_shapefile(
        cls,
        shape_path: Path,
        ElmID_col: str,
        VvN_col: Optional[str] = None,
        SBB_col: Optional[str] = None,
        vegtype_split_char: Optional[str] = None,
        datum_col: Optional[str] = None,
        opmerking_col: Optional[str] = None,
        # percentage_col: Optional[str] = None, # TODO: toevoegen support voor al bestaande percentage kolom
    ):
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile.
        Input:
        - shape_path: het pad naar de shapefile
        - ElmID_col: de kolomnaam van de ElementID in de Shapefile; uniek per vlak
        - VvN_col: kolomnaam van de VvN vegetatietypen als deze er zijn
        - SBB_col: kolomnaam van de SBB vegetatietypen als deze er zijn
        - vegtype_split_char: karakter waarop de vegetatietypen gesplitst moeten worden (voor complexen (bv "16aa2+15aa"))
        - datum_col: kolomnaam van de datum als deze er is
        - opmerking_col: kolomnaam van de opmerking als deze er is
        """
        # TODO: Voor nu gemaakt enkel voor de Groningen non-access karteringen, die hebben geen percentage kolom
        shapefile = gpd.read_file(shape_path)
        # Selectie van de te bewaren kolommen; VvN of SBB afhankelijk van wat is opgegeven,
        # datum en opmerking als deze er in zitten, en sowieso ElmID en geometry
        cols = (
            [col for col in [VvN_col, SBB_col] if col is not None]
            + [col for col in [datum_col, opmerking_col] if col in shapefile.columns]
            + [ElmID_col, "geometry"]
        )

        if not all(col in shapefile.columns for col in cols):
            raise ValueError(
                f"Niet alle opgegeven kolommen ({cols}) gevonden in de shapefile kolommen ({shapefile.columns})"
            )

        gdf = shapefile[cols].copy()

        # Als er geen datum of opmerking kolom is, dan vullen we deze met None
        datum_col = "Datum" if datum_col is None else datum_col
        opmerking_col = "Opmerking" if opmerking_col is None else opmerking_col
        for col in [datum_col, opmerking_col]:
            if col not in gdf.columns:
                gdf[col] = None

        # Standardiseren van kolomnamen
        gdf = gdf.rename(columns={datum_col: "Datum", opmerking_col: "Opmerking"})
        gdf["Opp"] = gdf["geometry"].area

        if VvN_col:
            gdf = ingest_vegtype_column(
                gdf, ElmID_col, VvN_col, _VvN, vegtype_split_char
            )
        elif SBB_col:
            # We pakken alleen SBB als er geen VvN is
            gdf = ingest_vegtype_column(
                gdf, ElmID_col, SBB_col, _SBB, vegtype_split_char
            )
        else:
            raise ValueError("Er is geen VvN of SBB kolomnaam opgegeven")

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
            ["Opp", "Opmerking", "Datum", "geometry", "VegTypeInfo", "HabitatKeuze"]
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

    def final_format_to_file(self, path: Path):
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

    def validate(self):
        pass
        # Validation error als t foute boel is

        # Validate aanwezigheid benodigde kolommen

        # Validate dat we of vvn of sbb hebben

        # Validate dat de geometrie een 2D multipolygon is

        # Validate dat de geometrie valide is (geen overlap, geen self intersection, etc)

        # Validate dat t rijksdriehoek is
