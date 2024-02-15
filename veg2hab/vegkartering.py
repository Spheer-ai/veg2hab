import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Type, Union

import geopandas as gpd
import pandas as pd

from veg2hab.criteria import BeperkendCriterium, Mozaiekregel
from veg2hab.enums import GoedMatig
from veg2hab.vegetatietypen import SBB as _SBB
from veg2hab.vegetatietypen import VvN as _VvN


@dataclass
class HabitatVoorstel:
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    vegtype: Union[_SBB, _VvN]
    habtype: str
    kwaliteit: GoedMatig
    regel_in_deftabel: int
    mits: Optional[BeperkendCriterium]
    mozaiek: Optional[Mozaiekregel]
    match_level: int
    percentage: int


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


class JoinParameters:
    """
    A set of parameters that is used for join operations. Can be chained together to create a join operation that joins multiple tables.
    """

    def __init__(self, csv_path, left_column, right_column):
        self.csv_path = csv_path
        self.left_column = left_column
        self.right_column = right_column


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
    gdf = gdf.copy()  # Needed to avoid SettingWithCopyWarning

    if vegtype_split_char:
        gdf["split_vegtypen"] = gdf[vegtype_col].str.split(vegtype_split_char)
    exploded = gdf.explode("split_vegtypen")
    gdf = gdf.drop(columns=["split_vegtypen"])

    # TODO: add support for already existing percentage_col
    # If there is no percentage column, we add it by evenly dividing the space in each shape
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


def hab_as_final_format(voorstel: HabitatVoorstel, idx: int, opp: float):
    return pd.Series(
        {
            f"Habtype{idx}": voorstel.habtype,
            f"Perc{idx}": voorstel.percentage,
            f"Opp{idx}": opp * voorstel.percentage,
            # f"ISHD{idx}" NOTE: Deze hoeft niet denk ik
            f"Kwal{idx}": voorstel.kwaliteit.as_letter()
            if voorstel.kwaliteit is not None
            else None,  # In H0000 gevallen is er geen kwaliteit (voorstel.kwaliteit is dan None)
            # f"Opm{idx}" NOTE: Ik weet niet wat ik hier moet zetten
            # f"Bron{idx}" NOTE: Ik weet niet wat ik hier moet zetten
            # f"HABcombi{idx}" NOTE: Deze hoeft niet denk ik
            f"VvN{idx}": str(voorstel.vegtype)
            if isinstance(voorstel.vegtype, _VvN)
            else None,
            f"SBB{idx}": str(voorstel.vegtype)
            if isinstance(voorstel.vegtype, _SBB)
            else None,
            # f"P{idx}" NOTE: Deze is altijd hetzelfde als Perc toch?
            # f"VEGlok{idx}" NOTE: Doen we voor nu nog even niet
        }
    )


def reorder_columns_final_format(df: pd.DataFrame):
    """
    Reorder de kolommen van een dataframe conform het Gegevens Leverings Protocol
    Result wil be:
    Area   Opm   geometry   Habtype1   Perc1   Opp1   Kwal1   VvN1   SBB1   Habtype2   Perc2   Opp2...
    """
    new_columns = ["Area", "Opm", "geometry"]
    n_habtype_blocks = len([i for i in df.columns if "Habtype" in i])
    for i in range(n_habtype_blocks):
        new_columns = new_columns + [
            f"Habtype{i}",
            f"Perc{i}",
            f"Opp{i}",
            f"Kwal{i}",
            f"VvN{i}",
            f"SBB{i}",
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
        gdf = gdf[["ElmID", "Datum", "Opmerking", "geometry"]]

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

        return cls(gdf)

    @classmethod
    def from_shapefile(
        cls,
        shape_path: Path,
        ElmID_col: str,
        VvN_col: Optional[str] = None,
        SBB_col: Optional[str] = None,
        vegtype_split_char: Optional[str] = None,
        # datum_col: Optional[str] = None, # mogelijk nodig 
        # percentage_col: Optional[str] = None, # TODO add support for already existing percentage_col
        # opmerking_col: Optional[str] = None, # mogelijk nodig
    ):
        """
        Deze method wordt gebruikt om een Kartering te maken van een shapefile.
        """
        # TODO: Voor nu gemaakt enkel voor de Groningen non-access karteringen, die hebben geen percentage kolom
        shapefile = gpd.read_file(shape_path)
        cols = [
            col for col in [ElmID_col, VvN_col, SBB_col, "geometry"] if col is not None
        ]

        assert all(
            col in shapefile.columns for col in cols
        ), f"Niet alle opgegeven kolommen ({cols}) gevonden in de shapefile kolommen ({shapefile.columns})"

        gdf = shapefile[[col for col in cols if col in shapefile.columns]]

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

    def as_final_format(self):
        """
        Output de kartering conform de beschrijving voor habitattypekarteringen zoals beschreven
        in het Gegevens Leverings Protocol (Bijlage 3a)
        """
        # NOTE: Voor nu behandelen de de HabitatVoorstellen als definitief
        self.gdf["HabitatDefinitief"] = self.gdf["HabitatVoorstel"]
        # NOTE: Voor nu nog even handmatig de "definitieve" habitattypen eenduidig maken
        self.gdf["HabitatDefinitief"] = self.gdf["HabitatDefinitief"].apply(
            lambda x: [i[0] for i in x if len(i) > 0] if len(x) > 0 else []
        )

        assert (
            "HabitatDefinitief" in self.gdf.columns
        ), "Er is geen kolom met definitieve habitatvoorstellen"

        # Base dataframe conform Gegevens Leverings Protocol maken
        base = self.gdf[["Opmerking", "geometry", "HabitatDefinitief"]]
        base = base.rename(columns={"Opmerking": "Opm"})
        base["Area"] = base["geometry"].area

        final = pd.concat([base, base.apply(self.row_to_final_format, axis=1)], axis=1)
        final = reorder_columns_final_format(final)
        return final

    def row_to_final_format(self, row):
        """
        Maakt van een rij een dataseries met blokken kolommen volgens het Gegevens Leverings Protocol (Bijlage 3a)
        """
        voorstellen = row["HabitatDefinitief"]
        if len(voorstellen) == 0:
            return pd.Series()

        return pd.concat(
            [
                hab_as_final_format(voorstel, i, row["Area"])
                for i, voorstel in enumerate(voorstellen)
            ]
        )

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
