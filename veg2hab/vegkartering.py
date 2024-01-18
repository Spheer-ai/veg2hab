from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd


class VegetatieTypeInfo:
    """
    Klasse met alle informatie over een vegetatietype van een vlak
    """

    def __init__(self, percentage: int, vvn: str = None, sbb: str = None):
        self.percentage = percentage
        self.vvn = vvn
        self.sbb = sbb

    @classmethod
    def create_list_from_access_rows(cls, rows: pd.DataFrame):
        """
        Maakt van alle rijen met vegetatietypes (van een vlak) een lijst van VegetatieTypeInfo objecten
        """
        lst = []
        for row in rows.itertuples():
            lst.append(cls(row.Bedekking_num, sbb=row.Sbb))
        return lst

    def __str__(self):
        return f"({self.percentage}%, vvn: '{self.vvn}', sbb: '{self.sbb}')"


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


class Veg2HabReadyKartering:
    """
    Een vegetatiekartering is klaar om gekoppeld te worden aan de definitietabel
    DWZ dat voor zover mogelijk de was-wordt lijst al is toegepast (en evt handmatig is gecorrigeerd)
    """

    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Validation van de gdf
        self.validate()

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


class ProtoKartering:
    """
    Deze kartering is nog niet omgezet naar VvN codes
    """

    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Validation van de gdf
        self.validate()

        # NOTE: evt iets van self.stage = lokaal/sbb/vvn ofzo?

    @classmethod
    def from_access_db(
        cls, shape_path: Path, shp_elm_id_column: str, access_csvs_path: Path
    ):
        """
        Deze method wordt gebruikt om een ProtoKartering te maken van een shapefile en een access database die al is opgedeeld in losse csv bestanden.

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
            element, left_on=shp_elm_id_column, right_on="ElmID", how="left"
        )

        # SBB code toevoegen aan KarteringVegetatietype
        kart_veg = kart_veg.merge(
            vegetatietype, left_on="Vegetatietype", right_on="Code", how="left"
        )
        kart_veg = kart_veg.merge(
            sbbtype, left_on="SbbType", right_on="Cata_ID", how="left"
        )

        # Groeperen van alle verschillende SBBs per Locatie
        grouped_kart_veg = (
            kart_veg.groupby("Locatie")
            .apply(VegetatieTypeInfo.create_list_from_access_rows)
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
        This method is used to create a ProtoKartering from a shapefile.
        """
        gdf = gpd.read_file(shape_path)
        return cls(gdf)

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
